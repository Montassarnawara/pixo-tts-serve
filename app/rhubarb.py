"""
rhubarb.py — Convertit l'audio en wav (ffmpeg) puis l'analyse avec Rhubarb Lip Sync pour en
extraire de vrais visèmes phonémiques.

Responsabilité unique (SRP) : audio en entrée, frames de visème en sortie. Ne sait rien de
comment l'audio a été généré (voir tts.py) ni de l'API HTTP (voir main.py).
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile

from app.settings import settings
from app.viseme_mapping import rhubarb_shape_to_viseme_id


class RhubarbError(RuntimeError):
    """Échec de la conversion audio (ffmpeg) ou de l'analyse labiale (Rhubarb)."""


def _convert_to_wav(mp3_path: str) -> str:
    wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    result = subprocess.run(
        [settings.ffmpeg_path, "-y", "-i", mp3_path, wav_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RhubarbError(f"Échec de la conversion audio (ffmpeg) : {result.stderr}")
    return wav_path


def _run_rhubarb(wav_path: str) -> list[dict]:
    output_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    try:
        result = subprocess.run(
            [settings.rhubarb_path, "-f", "json", wav_path, "-o", output_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RhubarbError(f"Échec de l'analyse Rhubarb : {result.stderr}")
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("mouthCues", [])
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


async def extract_visemes(mp3_path: str) -> list[dict]:
    """Convertit [mp3_path] en wav puis l'analyse avec Rhubarb. Retourne des frames au format
    `{"id": ..., "offset_ms": ...}`, directement compatibles avec le message `visemes` existant
    (voir visemes.md à la racine du dépôt).
    """
    wav_path = await asyncio.to_thread(_convert_to_wav, mp3_path)
    try:
        mouth_cues = await asyncio.to_thread(_run_rhubarb, wav_path)
    finally:
        os.remove(wav_path)
    return [
        {
            "id": rhubarb_shape_to_viseme_id(cue["value"]),
            "offset_ms": round(cue["start"] * 1000),
        }
        for cue in mouth_cues
    ]
