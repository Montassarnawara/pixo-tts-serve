import base64
import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
API_KEY = os.environ["TTS_SERVER_API_KEY"]


def test_synthesize_rejects_empty_text():
    response = client.post(
        "/synthesize", json={"text": "   "}, headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 422


def test_synthesize_returns_audio_and_frames(monkeypatch, tmp_path):
    fake_audio_path = tmp_path / "fake.mp3"
    fake_audio_path.write_bytes(b"fake-mp3-bytes")

    async def fake_synthesize_audio(text):
        return str(fake_audio_path)

    async def fake_extract_visemes(mp3_path):
        return [{"id": 20, "offset_ms": 0}, {"id": 0, "offset_ms": 500}]

    monkeypatch.setattr("app.main.synthesize_audio", fake_synthesize_audio)
    monkeypatch.setattr("app.main.extract_visemes", fake_extract_visemes)

    response = client.post(
        "/synthesize", json={"text": "Hello Pixo"}, headers={"X-API-Key": API_KEY}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["frames"] == [{"id": 20, "offset_ms": 0}, {"id": 0, "offset_ms": 500}]
    assert base64.b64decode(body["audio_base64"]) == b"fake-mp3-bytes"
    assert not fake_audio_path.exists()  # nettoyé après la requête


def test_synthesize_surfaces_rhubarb_failure(monkeypatch, tmp_path):
    fake_audio_path = tmp_path / "fake2.mp3"
    fake_audio_path.write_bytes(b"fake-mp3-bytes")

    async def fake_synthesize_audio(text):
        return str(fake_audio_path)

    async def failing_extract_visemes(mp3_path):
        from app.rhubarb import RhubarbError

        raise RhubarbError("ffmpeg introuvable")

    monkeypatch.setattr("app.main.synthesize_audio", fake_synthesize_audio)
    monkeypatch.setattr("app.main.extract_visemes", failing_extract_visemes)

    response = client.post(
        "/synthesize", json={"text": "Hello Pixo"}, headers={"X-API-Key": API_KEY}
    )

    assert response.status_code == 502
    assert not fake_audio_path.exists()  # nettoyé même en cas d'échec


def test_analyze_rejects_missing_api_key():
    response = client.post(
        "/analyze", files={"file": ("song.mp3", b"fake-mp3-bytes", "audio/mpeg")}
    )
    assert response.status_code == 401


def test_analyze_returns_frames(monkeypatch):
    async def fake_extract_visemes(mp3_path):
        assert os.path.exists(mp3_path)
        return [{"id": 20, "offset_ms": 0}, {"id": 0, "offset_ms": 500}]

    monkeypatch.setattr("app.main.extract_visemes", fake_extract_visemes)

    response = client.post(
        "/analyze",
        files={"file": ("song.mp3", b"fake-mp3-bytes", "audio/mpeg")},
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200
    assert response.json()["frames"] == [
        {"id": 20, "offset_ms": 0},
        {"id": 0, "offset_ms": 500},
    ]


def test_analyze_surfaces_rhubarb_failure(monkeypatch):
    async def failing_extract_visemes(mp3_path):
        from app.rhubarb import RhubarbError

        raise RhubarbError("ffmpeg introuvable")

    monkeypatch.setattr("app.main.extract_visemes", failing_extract_visemes)

    response = client.post(
        "/analyze",
        files={"file": ("song.mp3", b"fake-mp3-bytes", "audio/mpeg")},
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 502
