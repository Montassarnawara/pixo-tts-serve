from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_does_not_need_api_key():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_api_key_rejected():
    response = client.post("/synthesize", json={"text": "hello"})
    assert response.status_code == 401


def test_wrong_api_key_rejected():
    response = client.post(
        "/synthesize", json={"text": "hello"}, headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401
