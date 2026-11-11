"""Fixe une clé API de test AVANT que app.settings ne soit importé (il la lit à l'import)."""

import os

os.environ.setdefault("TTS_SERVER_API_KEY", "test-key")
