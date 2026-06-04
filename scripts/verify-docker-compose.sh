#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not installed"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "docker daemon not running — start Docker Desktop or the docker service"
  exit 1
fi

docker compose config >/dev/null
echo "docker compose config: OK"

required_services=(postgres redis minio api worker beat)
for svc in "${required_services[@]}"; do
  if ! docker compose config --services | grep -qx "$svc"; then
    echo "missing service in compose: $svc"
    exit 1
  fi
done

echo "All required services present: ${required_services[*]}"
