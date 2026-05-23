#!/bin/sh
set -eu

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

S3_BUCKET=${S3_BUCKET:-}
S3_PREFIX=${S3_PREFIX:-deepface-db-backups}
S3_ENDPOINT_URL=${S3_ENDPOINT_URL:-}
AWS_REGION=${AWS_REGION:-us-east-1}

POSTGRES_HOST=${POSTGRES_HOST:-database}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-}
POSTGRES_USER=${POSTGRES_USER:-}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-}

if [ -z "$S3_BUCKET" ]; then
  log "S3_BUCKET is required."
  exit 1
fi

if [ -z "$POSTGRES_DB" ] || [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ]; then
  log "PostgreSQL env is required (POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD)."
  exit 1
fi

TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
WORKDIR=/tmp/backup/$TIMESTAMP
mkdir -p "$WORKDIR"

export PGPASSWORD="$POSTGRES_PASSWORD"
log "Creating PostgreSQL dump..."
pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$WORKDIR/postgres.sql"

TARGET_BASE="s3://$S3_BUCKET/$S3_PREFIX/$TIMESTAMP"
log "Uploading to $TARGET_BASE..."

AWS_ARGS="--only-show-errors"
if [ -n "$S3_ENDPOINT_URL" ]; then
  AWS_ARGS="$AWS_ARGS --endpoint-url $S3_ENDPOINT_URL"
fi
if [ -n "$AWS_REGION" ]; then
  AWS_ARGS="$AWS_ARGS --region $AWS_REGION"
fi

aws s3 cp "$WORKDIR/postgres.sql" "$TARGET_BASE/postgres.sql" $AWS_ARGS

cat > "$WORKDIR/manifest.txt" <<EOF
created_at=$(date -Iseconds)
database_dump=postgres.sql
s3_bucket=$S3_BUCKET
s3_prefix=$S3_PREFIX
restore_hint=aws s3 cp $TARGET_BASE/postgres.sql - | psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB
EOF

aws s3 cp "$WORKDIR/manifest.txt" "$TARGET_BASE/manifest.txt" $AWS_ARGS

rm -rf "$WORKDIR"
log "Backup uploaded to $TARGET_BASE"
