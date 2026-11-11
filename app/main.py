"""
main.py — Point d'entrée FastAPI : assemble tts.py et rhubarb.py, expose l'API HTTP.

Responsabilité unique (SRP) : router les requêtes et mettre en forme les réponses. Toute la
logique vit dans tts.py, rhubarb.py, auth.py — ce fichier ne fait qu'assembler.
"""

from __future__ import annotations

import base64
import os
import tempfile

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from app.auth import require_api_key
from app.rhubarb import RhubarbError, extract_visemes
from app.tts import synthesize_audio

app = FastAPI(title="tts-server")


class SynthesizeRequest(BaseModel):
    text: str


class VisemeFrame(BaseModel):
    id: int
    offset_ms: int


class SynthesizeResponse(BaseModel):
    audio_base64: str
    frames: list[VisemeFrame]


class AnalyzeResponse(BaseModel):
    frames: list[VisemeFrame]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/synthesize",
    response_model=SynthesizeResponse,
    dependencies=[Depends(require_api_key)],
)
async def synthesize(payload: SynthesizeRequest) -> SynthesizeResponse:
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail="Le texte ne peut pas être vide.")

    audio_path = await synthesize_audio(payload.text)
    try:
        frames = await extract_visemes(audio_path)
        with open(audio_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("ascii")
    except RhubarbError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        os.remove(audio_path)

    return SynthesizeResponse(audio_base64=audio_base64, frames=frames)


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    dependencies=[Depends(require_api_key)],
)
async def analyze(file: UploadFile) -> AnalyzeResponse:
    """Analyse un audio déjà existant (ex: une chanson) avec Rhubarb — pas de synthèse, juste
    l'extraction de visèmes, pour les cas où l'audio ne vient pas de notre TTS (voir
    sing_with_me / song_hello.mp3)."""
    suffix = os.path.splitext(file.filename or "")[1] or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        frames = await extract_visemes(tmp_path)
    except RhubarbError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        os.remove(tmp_path)

    return AnalyzeResponse(frames=frames)
