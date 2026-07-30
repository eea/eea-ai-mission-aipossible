#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-mission-aipossible-test:local}"

docker build -f Dockerfile.test -t "$IMAGE_NAME" .
docker run --rm -v "$PWD:/workspace" -w /workspace "$IMAGE_NAME" bash -lc '
  pytest tests \
    --ignore=tests/test_analysis_api.py \
    --ignore=tests/test_run_analysis_api_script.py \
    --cov=analysis \
    --cov=api \
    --cov=pre_analysis \
    --cov=exporters \
    --cov=adaptation_stories \
    --cov=scripts \
    --cov=main \
    --cov=env_settings \
    --cov-report=term-missing
'
