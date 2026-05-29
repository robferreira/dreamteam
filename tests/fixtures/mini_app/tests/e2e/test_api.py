import os

import httpx


def test_health():
    base = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
    with httpx.Client(base_url=base, timeout=5) as client:
        r = client.get("/health")
        assert r.status_code == 200
