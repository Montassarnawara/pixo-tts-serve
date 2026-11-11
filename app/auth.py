"""
auth.py — Vérifie la clé API reçue dans l'en-tête X-API-Key.

Responsabilité unique (SRP) : valider la clé, rien d'autre. Ne sait rien de TTS ni de Rhubarb.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.settings import settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Dépendance FastAPI : lève 401 si la clé est absente ou incorrecte."""
    if x_api_key is None or x_api_key != settings.tts_server_api_key:
        raise HTTPException(status_code=401, detail="Clé API invalide ou manquante.")
