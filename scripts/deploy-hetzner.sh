#!/usr/bin/env bash
set -euo pipefail

REMOTE="${DEPLOY_HOST:-your-hetzner-host}"
REMOTE_DIR="${DEPLOY_DIR:-/opt/short-factory}"

echo "Deploying Short Factory to ${REMOTE}:${REMOTE_DIR}"

rsync -avz --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
  ./ "${REMOTE}:${REMOTE_DIR}/"

ssh "${REMOTE}" "cd ${REMOTE_DIR} && \
  docker compose pull && \
  docker compose build && \
  docker compose run --rm api alembic upgrade head && \
  docker compose up -d"

echo "Deploy complete. API should be available on port 8000."
