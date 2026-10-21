"""Central constants. Everything the Critic checks against lives here."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
MIN_DUR, MAX_DUR = 30.0, 60.0
ENDCARD_S = 4.5
MAX_FILE_MB = 100
TARGET_LUFS, LUFS_TOL, MAX_TRUE_PEAK = -14.0, 1.5, -1.0
MAX_LOOPS = 3
BUDGET_INR = 500.0
LIVE_RUN_SECONDS = 3 * 3600
DISCLOSURE = "Created with AI agents — LY Agentic AI Lab"
MIN_CAPTION_PX = 48           # at 1080 width
SAFE_TOP, SAFE_BOTTOM = 250, 350   # 9:16 platform UI overlays
WORDS_PER_SEC = 2.3           # spoken-pace estimate used by the Planner (re-calibrated from dry runs)
DEFAULT_FORBIDDEN = ["suicide method", "self-harm method", "kill yourself", "victim's face"]
SENSITIVE_CATEGORIES = ("Campus Safety", "Responsible AI")   # Category A and C

FONT_BOLD = ROOT / "assets/fonts/Poppins-Bold.ttf"
FONT_MED = ROOT / "assets/fonts/Poppins-Medium.ttf"
FONT_REG = ROOT / "assets/fonts/Poppins-Regular.ttf"
LOGO = ROOT / "assets/logo.png"   # official Somaiya Vidyavihar logo (empty margins cropped only; never recoloured/distorted)

FORMATS = {"video_9x16": (1080, 1920), "video_16x9": (1920, 1080)}


def env(name, default=None):
    """Read .env (if present) once, then os.environ."""
    if not getattr(env, "_loaded", False):
        p = ROOT / ".env"
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        env._loaded = True
    return os.environ.get(name, default)
