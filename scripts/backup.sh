#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-./backups/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$BACKUP_DIR"

echo "Backing up PostgreSQL..."
docker compose exec -T postgres pg_dump -U short_factory short_factory > "$BACKUP_DIR/postgres.sql"

echo "Backing up MinIO bucket metadata (list)..."
docker compose exec -T minio mc alias set local http://localhost:9000 minioadmin minioadmin >/dev/null 2>&1 || true
docker compose exec -T minio mc ls --recursive local/short-factory > "$BACKUP_DIR/minio-inventory.txt" 2>/dev/null || true

echo "Backup written to $BACKUP_DIR"
