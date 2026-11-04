from fastapi.testclient import TestClient
from app.main import app


def test_root_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "BrandCourt API"


def test_health_endpoint_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in ("ok", "degraded")
    assert payload["database"] in ("connected", "not_configured", "unavailable")
    assert payload["service"] == "BrandCourt API"
