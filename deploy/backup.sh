#!/bin/bash
# Database backup script for trading app
# Run this before any maintenance or updates

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="trading_db_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

echo "Starting database backup..."

docker exec trading_db pg_dump -U postgres trading > "${BACKUP_DIR}/${BACKUP_NAME}"

# Compress the backup
gzip "${BACKUP_DIR}/${BACKUP_NAME}"

echo "Backup created: ${BACKUP_DIR}/${BACKUP_NAME}.gz"

# Keep only last 7 backups
cd "$BACKUP_DIR"
ls -t trading_db_*.sql.gz | tail -n +8 | xargs -r rm -f

echo "Backup complete. Recent backups:"
ls -lh trading_db_*.sql.gz | head -5
