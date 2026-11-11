"""
tts.py — Génère l'audio à partir du texte, via edge-tts (gratuit, sans compte).

Responsabilité unique (SRP) : produire un fichier audio pour un texte donné. Ne sait rien
de Rhubarb ni du format de visème final — voir rhubarb.py pour la suite du pipeline.
"""

from __future__ import annotations

import tempfile

import edge_tts

# Voix "Cartoon/Conversation — Cute", conçue par Microsoft pour le contenu enfants — plus
# adaptée à Pixo qu'une voix adulte générique.
DEFAULT_VOICE = "en-US-AnaNeural"
# Légèrement ralentie : des pauses plus naturelles entre les phrases, moins pressé, plus doux.
DEFAULT_RATE = "-12%"


async def synthesize_audio(text: str, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> str:
    """Synthétise [text] et retourne le chemin du fichier mp3 généré (fichier temporaire)."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio_path = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
    return audio_path
