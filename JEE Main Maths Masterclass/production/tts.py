"""Narration synthesis with a content-addressed cache.

Every clip is synthesized once, normalised to 48 kHz mono, trimmed of
leading/trailing silence, and its true duration measured. Scenes are timed
from these measured durations (never from estimated word counts).
"""
import hashlib, json, os, subprocess, wave
import config as C

CACHE = os.path.join(C.CACHE, "tts")
os.makedirs(CACHE, exist_ok=True)

# Pronunciation lexicon: applied to the *spoken* text only (captions keep the
# written form). Keeps maths terms consistent across the whole series.
LEXICON = {
    "f(x)": "f of x",
    "g(x)": "g of x",
    "x²": "x squared",
    "|x|": "mod x",
    "−": " minus ",
}


def spoken(text):
    for k, v in LEXICON.items():
        text = text.replace(k, v)
    return text


class Clip:
    def __init__(self, path, dur, text):
        self.path, self.dur, self.text = path, dur, text


def _dur(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def synth(text):
    key = hashlib.sha1(json.dumps([C.TTS_BACKEND, C.TTS_VOICE.get(C.TTS_BACKEND),
                                   C.TTS_RATE_WPM, text]).encode()).hexdigest()[:16]
    out = os.path.join(CACHE, key + ".wav")
    if not os.path.exists(out):
        raw = out + ".raw.wav"
        say = spoken(text)
        if C.TTS_BACKEND == "espeak-ng":
            subprocess.run(["espeak-ng", "-v", C.TTS_VOICE["espeak-ng"], "-s", str(C.TTS_RATE_WPM),
                            "-w", raw, say], check=True)
        elif C.TTS_BACKEND == "piper":
            subprocess.run(["/opt/mvenv/bin/piper", "-m", C.TTS_VOICE["piper"], "-f", raw],
                           input=say.encode(), check=True)
        elif C.TTS_BACKEND == "recorded":
            src = os.path.join(C.ROOT, "audio", "recorded", key + ".wav")
            if not os.path.exists(src):
                raise FileNotFoundError(f"record line {key}: {text}")
            raw = src
        else:
            raise ValueError(C.TTS_BACKEND)
        # resample, trim silence at both ends, gentle high-pass for phone speakers
        subprocess.run(["sox", raw, "-r", str(C.AUDIO_SR), "-c", "1", "-b", "24", out,
                        "highpass", "70", "silence", "1", "0.02", "-55d", "reverse",
                        "silence", "1", "0.02", "-55d", "reverse"], check=True)
        if raw.endswith(".raw.wav"):
            os.remove(raw)
    return Clip(out, _dur(out), text)
