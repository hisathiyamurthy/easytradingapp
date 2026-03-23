#!/bin/bash
# Database backup script for EasyTradingApp
# Usage: ./backup.sh [daily|weekly|monthly]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/backup.conf"

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

BACKUP_TYPE="${1:-daily}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-/backups}"
S3_BUCKET="${S3_BUCKET:-}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-trading}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-}"

mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

upload_to_s3() {
    local file=$1
    if [ -n "$S3_BUCKET" ]; then
        log "Uploading $file to S3..."
        aws s3 cp "$file" "s3://${S3_BUCKET}/backups/${BACKUP_TYPE}/" --storage-class STANDARD_IA
        log "Upload complete"
    fi
}

cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
    log "Cleanup complete"
}

case "$BACKUP_TYPE" in
    daily)
        log "Starting daily backup..."
        filename="backup_daily_${TIMESTAMP}.sql.gz"
        ;;
    weekly)
        log "Starting weekly backup..."
        filename="backup_weekly_${TIMESTAMP}.sql.gz"
        ;;
    monthly)
        log "Starting monthly backup..."
        filename="backup_monthly_${TIMESTAMP}.sql.gz"
        RETENTION_DAYS=30
        ;;
    *)
        log "Unknown backup type: $BACKUP_TYPE"
        exit 1
        ;;
esac

BACKUP_PATH="${BACKUP_DIR}/${filename}"

export PGPASSWORD="$DB_PASSWORD"

log "Creating database backup..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -F c -b -v -f "$BACKUP_PATH" "$DB_NAME"

log "Compressing backup..."
gzip "$BACKUP_PATH"
BACKUP_PATH="${BACKUP_PATH}.gz"

log "Backup created: $BACKUP_PATH"
log "Backup size: $(du -h "$BACKUP_PATH" | cut -f1)"

upload_to_s3 "$BACKUP_PATH"

cleanup_old_backups

log "Backup process complete"

exit 0