from unittest.mock import patch

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


def test_analytics_dashboard_endpoints():
    with patch(
        "short_factory.analytics.collector.get_top_topics",
        return_value=[{"id": 1, "label": "Topic", "category": "breakups", "views": 10, "avg_retention": 0.8, "avg_ctr": 0.1, "score": 0.5}],
    ):
        response = client.get("/analytics/top-topics")
    assert response.status_code == 200
    assert response.json()[0]["label"] == "Topic"

    with patch(
        "short_factory.analytics.collector.get_top_scripts",
        return_value=[{"id": 2, "label": "Hook", "category": None, "views": 5, "avg_retention": 0.7, "avg_ctr": 0.09, "score": 0.45}],
    ):
        response = client.get("/analytics/top-scripts")
    assert response.status_code == 200
    assert response.json()[0]["id"] == 2
