"""Smoke tests against a live release-image container.

Unlike ``tests/``, these hit a real running server over HTTP rather than an
in-process ``TestClient`` — they verify the released container actually
boots, serves, and responds, not the application logic (already covered by
the unit suite). Point ``API_BASE_URL`` at the running container before
invoking pytest on this directory.
"""

import os

import httpx

BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")


def test_health_endpoint_reports_ok():
    response = httpx.get(f"{BASE_URL}/health", timeout=10)

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_use_cases_endpoint_returns_configured_names():
    response = httpx.get(f"{BASE_URL}/v1/analysis/use-cases", timeout=10)

    assert response.status_code == 200
    assert isinstance(response.json(), list)
