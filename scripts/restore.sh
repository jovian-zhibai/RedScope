#!/bin/bash
# RedScope PostgreSQL restore script
# Usage: ./restore.sh <backup_file>
# Example: ./restore.sh backups/redscope_20260625_030000.sql.gz

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "[ERROR] Usage: ./restore.sh <backup_file.sql.gz>"
    echo "Available backups:"
    ls -lt backups/redscope_*.sql.gz 2>/dev/null | head -10
    exit 1
fi

DB_CONTAINER=$(docker compose ps -q db 2>/dev/null)
if [ -z "$DB_CONTAINER" ]; then
    echo "[ERROR] Database container not found."
    exit 1
fi

echo "[WARNING] This will OVERWRITE the current database!"
read -p "Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo "[INFO] Stopping backend services..."
docker compose stop backend celery_worker

echo "[INFO] Restoring from $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U redscope -d redscope

if [ $? -eq 0 ]; then
    echo "[OK] Restore complete"
else
    echo "[ERROR] Restore failed"
fi

echo "[INFO] Restarting services..."
docker compose start backend celery_worker
echo "[INFO] Done"
