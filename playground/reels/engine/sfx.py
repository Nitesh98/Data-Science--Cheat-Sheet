"""
Tiny sound-design synthesizer (standard library only). Turns the cue list a reel registers with
M.cue(t, type) into a stereo WAV: hits, pops, ticks, whooshes, risers, buzzes and chimes.

Muted/removable by design: Instagram lets you layer trending music on top in the app.
"""
import math
import random
import struct
import wave

SR = 44100


def _env(i, n, attack=0.004, power=3.0):
    """Fast attack, exponential-ish decay."""
    a = max(1, int(attack * SR))
    return (i / a) if i < a else (1 - (i - a) / max(1, n - a)) ** power


def hit(vol=1.0):
    n = int(0.55 * SR)
    rnd = random.Random(5)
    out = []
    for i in range(n):
        t = i / SR
        f = 45 + 120 * math.exp(-t * 14)                 # pitch drops: a punchy sub thump
        thump = math.sin(2 * math.pi * f * t) * _env(i, n, 0.002, 2.2)
        click = (rnd.random() * 2 - 1) * math.exp(-t * 60) * 0.55
        out.append((thump * 1.0 + click) * vol)
    return out


def pop(vol=0.5, pitch=1.0):
    n = int(0.09 * SR)
    f0 = 620 * pitch
    return [math.sin(2 * math.pi * (f0 + 500 * math.exp(-i / SR * 70)) * i / SR) * _env(i, n, 0.001, 2.0) * vol
            for i in range(n)]


def tick(vol=0.35):
    n = int(0.03 * SR)
    return [math.sin(2 * math.pi * 2600 * i / SR) * _env(i, n, 0.0005, 3.0) * vol for i in range(n)]


def whoosh(vol=0.5, dur=0.6):
    n = int(dur * SR)
    rnd = random.Random(11)
    out, lp = [], 0.0
    for i in range(n):
        p = i / n
        cutoff = 0.02 + 0.5 * math.sin(math.pi * p) ** 2           # filter sweeps open then closed
        lp += cutoff * ((rnd.random() * 2 - 1) - lp)
        out.append(lp * math.sin(math.pi * p) ** 1.4 * vol * 3.2)
    return out


def riser(vol=0.35, dur=1.2):
    n = int(dur * SR)
    rnd = random.Random(21)
    out, lp = [], 0.0
    for i in range(n):
        p = i / n
        lp += (0.03 + 0.4 * p) * ((rnd.random() * 2 - 1) - lp)
        tone = math.sin(2 * math.pi * (180 + 1500 * p * p) * i / SR) * 0.4
        out.append((lp * 2.4 + tone) * p ** 1.8 * vol)
    return out


def buzz(vol=0.4, dur=0.45):
    n = int(dur * SR)
    out = []
    for i in range(n):
        t = i / SR
        sq = 1.0 if math.sin(2 * math.pi * 92 * t) > 0 else -1.0
        sq2 = 1.0 if math.sin(2 * math.pi * 97 * t) > 0 else -1.0
        out.append((sq + sq2) * 0.5 * (0.6 + 0.4 * math.sin(2 * math.pi * 22 * t)) * _env(i, n, 0.003, 1.2) * vol * 0.5)
    return out


def chime(vol=0.4):
    notes = [1046.5, 1318.5, 1568.0, 2093.0]          # C6 E6 G6 C7
    n = int(1.1 * SR)
    out = [0.0] * n
    for k, f in enumerate(notes):
        start = int(k * 0.075 * SR)
        for i in range(n - start):
            t = i / SR
            out[start + i] += math.sin(2 * math.pi * f * t) * math.exp(-t * 4.2) * vol * 0.35
    return out


GENERATORS = {"hit": hit, "pop": pop, "tick": tick, "whoosh": whoosh, "riser": riser, "buzz": buzz, "chime": chime}


def render(cues, duration, path):
    n = int((duration + 0.5) * SR)
    mix = [0.0] * n
    for c in cues:
        gen = GENERATORS.get(c["type"])
        if not gen:
            continue
        args = {"vol": c["v"]} if c.get("v") is not None and c["type"] != "pop" else {}
        if c["type"] == "pop" and c.get("v") is not None:
            args = {"pitch": c["v"]}
        s = gen(**args)
        start = int(c["t"] * SR)
        for i, v in enumerate(s):
            if start + i < n:
                mix[start + i] += v
    peak = max(1e-9, max(abs(v) for v in mix))
    scale = 0.85 / max(peak, 0.85)                       # only ever turn DOWN; then soft-clip
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = bytearray()
        for v in mix:
            s = int(math.tanh(v * scale * 1.1) * 32000)
            frames += struct.pack("<hh", s, s)
        w.writeframes(bytes(frames))
