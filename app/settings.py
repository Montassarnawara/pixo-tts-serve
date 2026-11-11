"""
settings.py — Lecture de la configuration depuis l'environnement (voir .env.example).

Responsabilité unique (SRP) : charger et valider la config, rien d'autre. Les autres
modules importent `settings` plutôt que de lire os.environ directement.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    tts_server_api_key: str
    port: int = 8080
    rhubarb_path: str = "rhubarb"
    ffmpeg_path: str = "ffmpeg"


settings = Settings()
