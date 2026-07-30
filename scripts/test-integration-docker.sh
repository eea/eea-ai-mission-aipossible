#!/usr/bin/env bash
set -euo pipefail

TEST_IMAGE="${TEST_IMAGE:-mission-aipossible-test:local}"
RELEASE_IMAGE="${RELEASE_IMAGE:-mission-aipossible-release:local}"
PORT="${PORT:-18000}"

cleanup() {
  docker stop mission-aipossible-api-test >/dev/null 2>&1 || true
  docker rm -v mission-aipossible-api-test >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker build -f Dockerfile.test -t "$TEST_IMAGE" .
docker build -t "$RELEASE_IMAGE" .
mkdir -p .jenkins-fixtures
printf '{"smoke_use_case": {}}' > .jenkins-fixtures/analysis_use_cases.json

docker run -d \
  --name mission-aipossible-api-test \
  -p 127.0.0.1:${PORT}:8000 \
  -v "$PWD/.jenkins-fixtures:/fixtures" \
  -e OUTPUT_DIR=/app/data/analysis \
  -e EXPORT_DIR=/app/data/exports \
  -e PROVIDER=mock \
  -e API_USE_CASES_CONFIG=/fixtures/analysis_use_cases.json \
  "$RELEASE_IMAGE"

for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null && break
  sleep 2
done
curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null
curl -fsS "http://127.0.0.1:${PORT}/v1/analysis/use-cases" >/dev/null

docker run --rm -v "$PWD:/workspace" -w /workspace "$TEST_IMAGE" bash -lc '
  pytest tests/test_analysis_api.py tests/test_run_analysis_api_script.py
'
