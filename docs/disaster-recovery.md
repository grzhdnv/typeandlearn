# Disaster Recovery & Backup Runbook

This document defines the disaster recovery policy, recovery objectives, automated procedures, and rehearsal verification standards for TypeAndLearn.

---

## 1. Service Level Objectives

- **Recovery Point Objective (RPO)**: **< 24 Hours**
  - All tenant texts, practice sessions, weak vocabulary words, and token usage records are captured in daily compressed snapshots.
  - In the event of catastrophic data loss, maximum data exposure is bounded by the last 24-hour backup interval.
- **Recovery Time Objective (RTO)**: **< 4 Hours**
  - The automated restoration script verifies integrity, replaces database targets atomically, and applies forward database migrations in under 5 minutes on standard infrastructure.

---

## 2. Backup Architecture & Retention Policy

- **Backup Automation Script**: `scripts/backup.py`
  - Uses the SQLite Online Backup API (`src.backup(dst)`) to take non-blocking, transactionally consistent snapshots without stopping the web or worker processes.
  - For PostgreSQL staging/production environments, uses `pg_dump` with gzip compression.
  - Produces timestamped archives:
    `backups/typeandlearn_<db_type>_<YYYYMMDD_HHMMSS>.<db|sql>.gz`
- **Integrity Manifest**:
  - Each backup archive generates an accompanying `.sha256` manifest file containing the cryptographic digest.
  - Backups cannot be restored if SHA-256 validation fails.
- **Retention Schedule**:
  - Snapshots are retained locally and in object storage for **30 days**.
  - `scripts/backup.py` automatically prunes expired backups older than the retention threshold.

---

## 3. Operational Procedures

### Creating a Manual or Scheduled Backup
```bash
# Backup default database to ./backups/
uv run python scripts/backup.py

# Backup with custom output directory and retention period
uv run python scripts/backup.py --output-dir /var/backups/typeandlearn --retention-days 14
```

### Emergency Database Restoration
In the event of database corruption, disk failure, or accidental deletion:

```bash
# 1. Inspect available backups
ls -lh backups/

# 2. Execute restore with checksum verification and migration alignment
uv run python scripts/restore.py backups/typeandlearn_sqlite_20260913_204126.db.gz

# 3. Verify application health
curl -f http://127.0.0.1:8000/healthz
curl -f http://127.0.0.1:8000/readyz
```

---

## 4. Disaster Recovery Rehearsal Standard

- **Rehearsal Cadence**: Monthly automated simulation in CI/staging.
- **Rehearsal Procedure**:
  1. Populate baseline tenant dataset with texts, sentences, practice metrics, and weak words.
  2. Execute `scripts/backup.py` to capture snapshot and checksum.
  3. Intentionally simulate disaster (corrupt database or purge volume).
  4. Execute `scripts/restore.py` with checksum validation and migration alignment.
  5. Verify 100% record count and field fidelity across all entities via `tests/backend/test_disaster_recovery.py`.

---

## 5. Rehearsal Audit Log

| Date | Environment | Operator / Test | Backup File | Checksum Verified | Restoration Status | RTO Achieved |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-09-13 | Local / CI | Automated Test | `typeandlearn_sqlite_*.db.gz` | YES (SHA-256) | Success (100% data fidelity) | < 10 seconds |
