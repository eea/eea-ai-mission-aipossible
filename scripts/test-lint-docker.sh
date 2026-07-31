#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-mission-aipossible-test:local}"

docker build -f Dockerfile.test -t "$IMAGE_NAME" .
docker run --rm -v "$PWD:/workspace" -w /workspace "$IMAGE_NAME" bash -lc '
  ruff check analysis api pre_analysis exporters scripts adaptation_stories tests main.py env_settings.py --select E,F,W,I,B,C,N,Q,RUF --ignore D &&
  black --check analysis api pre_analysis exporters scripts adaptation_stories tests main.py env_settings.py &&
  mypy analysis api pre_analysis exporters scripts adaptation_stories &&
  cd /app/ui && npm run build
'
