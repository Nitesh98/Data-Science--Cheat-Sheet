"""Every knob for Muse in one place. Override any of them with environment variables."""
import os
from pathlib import Path

MODEL = os.environ.get("MUSE_MODEL", "claude-opus-5")

# How hard Muse thinks per reply: low | medium | high | xhigh | max.
# "medium" keeps everyday chat snappy; raise it for heavy research/planning.
EFFORT = os.environ.get("MUSE_EFFORT", "medium")
REFLECT_EFFORT = "low"            # end-of-session memory extraction is an easy job

MAX_TOKENS = 64000                # streaming, so a large ceiling is safe
MAX_TOOL_ROUNDS = 25              # hard stop for one reply's agent loop
MAX_PAUSE_RESUMES = 5             # server web-search loop continuations per reply

# If Claude's safety classifiers decline a request, the API re-runs it on the
# model Anthropic recommends for that refusal category instead of failing.
BETAS = ["server-side-fallback-2026-07-01"]
FALLBACKS = "default"

# Everything Muse knows about you lives in ONE local SQLite file, never in this repo.
HOME = Path(os.environ.get("MUSE_HOME", Path.home() / ".muse"))
DB_PATH = HOME / "muse.db"

# How much remembered context is injected into each turn.
PROFILE_FACTS = 12                # highest-importance facts, always included
RELEVANT_FACTS = 8                # facts retrieved for *this* message
RELEVANT_NOTES = 3
