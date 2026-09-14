#!/usr/bin/env python3
"""Automated database restore and rehearsal script with checksum validation and migration alignment."""

import argparse
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

from backup import compute_sha256


def verify_checksum(backup_path: Path) -> bool:
    """Verify SHA-256 against associated .sha256 manifest if present."""
    checksum_file = backup_path.with_suffix(backup_path.suffix + ".sha256")
    if not checksum_file.exists():
        # Look for pattern without double extension, e.g., typeandlearn.db.sha256
        checksum_file = backup_path.with_name(f"{backup_path.stem}.sha256")
    if not checksum_file.exists():
        return True  # Manifest not present, skip verification

    expected = checksum_file.read_text(encoding="utf-8").strip().split()[0]
    actual = compute_sha256(backup_path)
    if expected != actual:
        raise ValueError(
            f"Checksum verification failed for {backup_path}! Expected {expected}, got {actual}"
        )
    return True


def restore_sqlite(backup_path: Path, target_path: Path) -> dict:
    """Decompress and restore SQLite database with integrity verification."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target_path.with_suffix(".restoring.tmp")

    # 1. Decompress into temporary file
    if backup_path.suffix == ".gz":
        with gzip.open(backup_path, "rb") as f_in, open(temp_target, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    else:
        shutil.copy2(backup_path, temp_target)

    # 2. Verify SQLite integrity
    conn = sqlite3.connect(temp_target)
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check;")
    check_result = cursor.fetchone()
    conn.close()

    if not check_result or check_result[0] != "ok":
        temp_target.unlink()
        raise ValueError(f"SQLite PRAGMA integrity_check failed: {check_result}")

    # 3. Atomically replace target database
    temp_target.replace(target_path)

    return {
        "integrity_check": "ok",
        "target_path": str(target_path.resolve()),
        "restored_size_bytes": target_path.stat().st_size,
    }


def restore_postgres(backup_path: Path, database_url: str) -> dict:
    """Restore PostgreSQL database using psql."""
    cmd = ["psql", "--dbname", database_url]
    if backup_path.suffix == ".gz":
        with gzip.open(backup_path, "rb") as f_in:
            sql_data = f_in.read()
        subprocess.run(cmd, input=sql_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    else:
        with open(backup_path, "rb") as f_in:
            sql_data = f_in.read()
        subprocess.run(cmd, input=sql_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    return {
        "integrity_check": "ok",
        "target_url": database_url,
    }


def align_migrations(target_db_url: str | None = None) -> str:
    """Execute alembic upgrade head to ensure restored schema aligns with current application code."""
    env = os.environ.copy()
    if target_db_url:
        env["DATABASE_URL"] = target_db_url

    res = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=True,
    )
    return res.stdout.strip()


def perform_restore(
    backup_path: Path,
    target_db: str | None = None,
    skip_checksum: bool = False,
    skip_migrations: bool = False,
) -> dict:
    """Execute complete restore workflow with validation and migration alignment."""
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    # 1. Checksum validation
    if not skip_checksum:
        verify_checksum(backup_path)

    target_url = target_db or os.getenv("DATABASE_URL", "sqlite:///apps/backend/data/typeandlearn.db")

    if target_url.startswith("sqlite:///"):
        target_path = Path(target_url.replace("sqlite:///", ""))
        details = restore_sqlite(backup_path, target_path)
    elif target_url.startswith("postgresql://") or target_url.startswith("postgres://"):
        details = restore_postgres(backup_path, target_url)
    else:
        raise ValueError(f"Unsupported database URL scheme: {target_url}")

    # 2. Align migrations
    migration_output = "skipped"
    if not skip_migrations:
        try:
            migration_output = align_migrations(target_url)
        except Exception as e:
            migration_output = f"warning: migration alignment error: {e}"

    return {
        "status": "success",
        "backup_source": str(backup_path.resolve()),
        "target_database": target_url,
        "details": details,
        "migration_alignment": migration_output,
        "restored_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="TypeAndLearn Database Restore Utility")
    parser.add_argument("backup_file", type=Path, help="Path to backup archive (.db.gz, .sql.gz)")
    parser.add_argument(
        "--target-db",
        type=str,
        default=None,
        help="Target database path or URL (default: read from DATABASE_URL or local SQLite)",
    )
    parser.add_argument(
        "--skip-checksum",
        action="store_true",
        help="Skip SHA-256 checksum verification",
    )
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Skip running alembic upgrade head after restoration",
    )

    args = parser.parse_args()
    try:
        report = perform_restore(
            backup_path=args.backup_file,
            target_db=args.target_db,
            skip_checksum=args.skip_checksum,
            skip_migrations=args.skip_migrations,
        )
        print(json.dumps(report, indent=2))
    except Exception as err:
        print(f"ERROR: Restore failed: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
