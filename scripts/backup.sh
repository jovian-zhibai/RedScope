#!/bin/bash
# RedScope PostgreSQL backup script
# Usage: ./backup.sh [backup_dir]
# Recommended: add to crontab for daily backups
#   0 3 * * * /path/to/backup.sh /path/to/backups

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/redscope_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

# Get DB container name
DB_CONTAINER=$(docker compose ps -q db 2>/dev/null)
if [ -z "$DB_CONTAINER" ]; then
    echo "[ERROR] Database container not found. Is docker compose running?"
    exit 1
fi

echo "[INFO] Starting backup at $(date)"
docker exec "$DB_CONTAINER" pg_dump -U redscope redscope | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[OK] Backup saved: $BACKUP_FILE ($SIZE)"
else
    echo "[ERROR] Backup failed"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Keep only last 30 backups
ls -t "$BACKUP_DIR"/redscope_*.sql.gz 2>/dev/null | tail -n +31 | xargs rm -f 2>/dev/null
KEPT=$(ls "$BACKUP_DIR"/redscope_*.sql.gz 2>/dev/null | wc -l)
echo "[INFO] Retention: keeping $KEPT backups (max 30)"
echo "[INFO] Backup complete at $(date)"
