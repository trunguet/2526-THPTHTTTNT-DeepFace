#!/usr/bin/env bash
set -euo pipefail

TS=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_DIR:-/backups}"
DEST="$BACKUP_DIR/$TS"
mkdir -p "$DEST"

echo "[backup] start: $TS"
echo "[backup] dest:  $DEST"

: "${MYSQL_HOST:?MYSQL_HOST is required}"
: "${MYSQL_DATABASE:?MYSQL_DATABASE is required}"
: "${MYSQL_USER:?MYSQL_USER is required}"
: "${MYSQL_PASSWORD:?MYSQL_PASSWORD is required}"

export MYSQL_PWD="$MYSQL_PASSWORD"
echo "[backup] mysql: dumping $MYSQL_DATABASE"
mysqldump -h "$MYSQL_HOST" -u "$MYSQL_USER" \
  --single-transaction --routines --triggers "$MYSQL_DATABASE" > "$DEST/mysql.sql"
unset MYSQL_PWD

if [ -d /data/minio ]; then
  echo "[backup] minio: /data/minio -> minio_data.tar.gz"
  tar -czf "$DEST/minio_data.tar.gz" -C /data/minio .
fi

if [ -d /data/qdrant ]; then
  echo "[backup] qdrant: /data/qdrant -> qdrant_data.tar.gz"
  tar -czf "$DEST/qdrant_data.tar.gz" -C /data/qdrant .
fi

if [ "${ENABLE_REDIS_BACKUP:-false}" = "true" ] && [ -d /data/redis ]; then
  echo "[backup] redis: /data/redis -> redis_data.tar.gz"
  tar -czf "$DEST/redis_data.tar.gz" -C /data/redis .
fi

RETENTION_DAYS="${RETENTION_DAYS:-7}"
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} +

echo "[backup] done"