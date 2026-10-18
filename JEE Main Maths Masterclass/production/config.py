"""Production-wide configuration. Change values here, not inside scenes."""
import os

# The pipeline lives in the Maths project and is shared by the series: set
# JEE_PROJECT to another subject's folder (e.g. "JEE Main Physics Masterclass")
# and renders, timelines and the chapter list come from that project instead.
PROD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("JEE_PROJECT") or os.path.dirname(PROD)
RENDERS = os.path.join(ROOT, "renders")
CACHE = os.path.join(RENDERS, "cache")

# --- video -------------------------------------------------------------------
WIDTH, HEIGHT, FPS = 3840, 2160, 30          # native 4K composition
PREVIEW = os.environ.get("JEE_PREVIEW") == "1"  # 1280x720@15 for fast drafts (never shipped)

# --- narration ---------------------------------------------------------------
# Backend is swappable without touching scenes. The animation timing follows the
# *measured* duration of each synthesized clip, so changing the voice and
# re-running build.py re-times every scene automatically.
TTS_BACKEND = os.environ.get("JEE_TTS", "espeak-ng")   # espeak-ng | piper | recorded
TTS_VOICE = {"espeak-ng": "hi", "piper": "/opt/voices/hi_IN-pratham-medium.onnx"}
TTS_RATE_WPM = 150
SENTENCE_GAP = 0.35        # seconds of air between caption chunks
AUDIO_SR = 48000

# --- loudness targets ----------------------------------------------------------
TARGET_LUFS = -14.0
TARGET_TP = -1.0
MUSIC_DB_UNDER_VOICE = -24.0   # music bed relative to narration while speaking
MUSIC_DB_ALONE = -18.0         # music when nobody speaks (title cards, pauses)

# --- chapter list for the progress indicator -----------------------------------
def _chapter_ids():
    import importlib.util
    path = os.path.join(ROOT, "docs", "coverage_data.py")
    spec = importlib.util.spec_from_file_location("coverage_data", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.CHAPTERS)


CHAPTER_IDS = _chapter_ids()
