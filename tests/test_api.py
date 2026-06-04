from fastapi.testclient import TestClient

from short_factory.api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_page():
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Short Factory Admin" in response.text
