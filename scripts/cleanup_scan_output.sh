#!/bin/bash
# RedScope scan output cleanup
# Removes scan output directories older than 30 days
# Usage: add to crontab: 0 4 * * * /path/to/cleanup_scan_output.sh

SCAN_DIR="/app/output"
DAYS_TO_KEEP=${1:-30}

if [ ! -d "$SCAN_DIR" ]; then
    echo "[INFO] Scan output directory not found: $SCAN_DIR"
    exit 0
fi

echo "[INFO] Cleaning scan output older than $DAYS_TO_KEEP days..."
BEFORE=$(du -sh "$SCAN_DIR" 2>/dev/null | cut -f1)

find "$SCAN_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +$DAYS_TO_KEEP -exec rm -rf {} \; 2>/dev/null
find "$SCAN_DIR/screenshots" -type f -mtime +90 -delete 2>/dev/null

AFTER=$(du -sh "$SCAN_DIR" 2>/dev/null | cut -f1)
echo "[OK] Cleanup complete: $BEFORE → $AFTER"
