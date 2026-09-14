#!/usr/bin/env python3
"""Automated database backup script with gzip compression and SHA-256 verification."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hexadecimal digest of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def backup_sqlite(source_path: Path, output_dir: Path) -> Path:
    """Perform a transactional SQLite backup and gzip-compress the result."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_target = output_dir / f"typeandlearn_sqlite_{timestamp}.db"
    compressed_target = output_dir / f"typeandlearn_sqlite_{timestamp}.db.gz"

    # Use SQLite online backup API to ensure snapshot consistency even under concurrent writes
    src_conn = sqlite3.connect(source_path)
    dst_conn = sqlite3.connect(raw_target)
    with src_conn, dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()

    # Compress the snapshot
    with open(raw_target, "rb") as f_in, gzip.open(compressed_target, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

    # Remove uncompressed raw backup
    raw_target.unlink()

    return compressed_target


def backup_postgres(database_url: str, output_dir: Path) -> Path:
    """Dump PostgreSQL database using pg_dump into a gzip-compressed archive."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    compressed_target = output_dir / f"typeandlearn_postgres_{timestamp}.sql.gz"

    cmd = ["pg_dump", "--dbname", database_url]
    with gzip.open(compressed_target, "wb") as f_out:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        f_out.write(proc.stdout)

    return compressed_target


def prune_old_backups(output_dir: Path, retention_days: int) -> int:
    """Delete backup archives older than retention_days."""
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - (retention_days * 86400)
    pruned_count = 0

    for item in output_dir.glob("typeandlearn_*.*"):
        if item.is_file() and item.stat().st_mtime < cutoff:
            item.unlink()
            pruned_count += 1

    return pruned_count


def create_backup(
    output_dir: Path,
    database_url: str | None = None,
    retention_days: int = 30,
) -> dict:
    """Create timestamped database backup and checksum manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    db_url = database_url or os.getenv("DATABASE_URL", "sqlite:///apps/backend/data/typeandlearn.db")

    if db_url.startswith("sqlite:///"):
        sqlite_path = Path(db_url.replace("sqlite:///", ""))
        if not sqlite_path.exists():
            # If default doesn't exist yet, create an empty SQLite file for baseline
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(sqlite_path) as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS _baseline_init (id INTEGER PRIMARY KEY);")
        backup_file = backup_sqlite(sqlite_path, output_dir)
        db_type = "sqlite"
    elif db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        backup_file = backup_postgres(db_url, output_dir)
        db_type = "postgresql"
    else:
        raise ValueError(f"Unsupported database URL scheme: {db_url}")

    # Compute SHA-256 checksum
    checksum = compute_sha256(backup_file)
    checksum_file = backup_file.with_suffix(backup_file.suffix + ".sha256")
    checksum_file.write_text(f"{checksum}  {backup_file.name}\n", encoding="utf-8")

    # Prune expired backups
    pruned = prune_old_backups(output_dir, retention_days)

    return {
        "status": "success",
        "database_type": db_type,
        "backup_file": str(backup_file.resolve()),
        "checksum_file": str(checksum_file.resolve()),
        "sha256": checksum,
        "size_bytes": backup_file.stat().st_size,
        "pruned_old_backups": pruned,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="TypeAndLearn Database Backup Utility")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backups"),
        help="Directory to store backup files (default: backups)",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Database URL (default: read from DATABASE_URL or fallback to local SQLite)",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Retention period in days for older backups (default: 30)",
    )

    args = parser.parse_args()
    try:
        report = create_backup(
            output_dir=args.output_dir,
            database_url=args.database_url,
            retention_days=args.retention_days,
        )
        print(json.dumps(report, indent=2))
    except Exception as err:
        print(f"ERROR: Backup failed: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
