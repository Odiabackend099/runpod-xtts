#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.testsprite.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Docker is required. Please install Docker Desktop (https://www.docker.com/products/docker-desktop/)" >&2
  exit 1
fi

echo "🧹 Stopping any previous TestSprite stack..."
docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans >/dev/null 2>&1 || true

echo "🚀 Starting TestSprite automation (Redis + TTS service + TestSprite)..."
docker compose -f "$COMPOSE_FILE" up --build --abort-on-container-exit

EXIT_CODE=$?

echo "🧹 Cleaning up containers..."
docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans >/dev/null 2>&1

if [ $EXIT_CODE -eq 0 ]; then
  echo "✅ TestSprite run completed successfully."
  echo "📂 Check container logs above for details."
else
  echo "❌ TestSprite run failed (exit code $EXIT_CODE)."
  echo "🔎 Review the logs above to diagnose the failure."
fi

exit $EXIT_CODE
