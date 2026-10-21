"""Pre-download the free neural voice (Kokoro, ~115 MB, Apache-2.0).  python -m tools.download_models
Happens automatically on first run too; use this once on good wifi before the Live Run."""
from core import tts
tts.ensure_models()
print("models ready in", tts.MODEL_DIR)
