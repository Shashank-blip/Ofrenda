from fastapi.testclient import TestClient

from app.server import app


def test_sample_grave_and_health():
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert "model" in health.json()

        response = client.get("/api/sample")
        assert response.status_code == 200
        grave = response.json()["graves"][0]
        assert grave["name"] == "hourglass"
        assert grave["last_on"] == "2023-02-14"
        assert grave["last_subject"] == "Leave a warning about months before stopping"
        assert any("months are not the same length" in item["text"] for item in grave["todos"])


def test_missing_path_is_400():
    with TestClient(app) as client:
        response = client.post("/api/altar", json={"path": "D:\\this\\folder\\is\\not\\real\\ofrenda"})
        assert response.status_code == 400
