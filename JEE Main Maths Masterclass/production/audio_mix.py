"""Build the soundtrack for a scene from its timeline JSON.

All music and effects are synthesised here from first principles (sine
partials, filtered noise, envelopes) — they are original works of this
production and need no third-party licence.

Mix design
* narration: mono, centred in both channels (mono-compatible by design);
* music: a sparse pad, sidechain-ducked under the voice, switched 'low'
  during prediction pauses and 'off' during dense reasoning and right before
  corrections ("brief silence before a crucial correction");
* effects: few, quiet, and tied to meaning (see SFX below);
* master: two-pass EBU R128 loudnorm to -14 LUFS integrated, -1 dBTP.
"""
import json, os, subprocess, sys, wave
import numpy as np
import config as C

SR = C.AUDIO_SR


def db(x):
    return 10 ** (x / 20)


def read_wav(path):
    with wave.open(path) as w:
        n, sw, ch = w.getnframes(), w.getsampwidth(), w.getnchannels()
        raw = w.readframes(n)
    if sw == 3:
        a = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        a = (a[:, 0].astype(np.int32) | (a[:, 1].astype(np.int32) << 8) | (a[:, 2].astype(np.int32) << 16))
        a = np.where(a >= 2 ** 23, a - 2 ** 24, a) / 2 ** 23
    else:
        a = np.frombuffer(raw, np.int16) / 32768.0
    return a.reshape(-1, ch).mean(axis=1).astype(np.float32)


def env(n, a, r):
    e = np.ones(n, np.float32)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def tone(freq, dur, partials=((1, 1.0),), decay=None):
    t = np.arange(int(dur * SR)) / SR
    s = sum(g * np.sin(2 * np.pi * freq * k * t) for k, g in partials)
    if decay:
        s *= np.exp(-t / decay)
    return s.astype(np.float32)


def noise_swell(dur=0.7):
    rng = np.random.default_rng(7)
    n = int(dur * SR)
    x = rng.standard_normal(n).astype(np.float32)
    # cheap band-limit: moving averages
    x = np.convolve(x, np.ones(24) / 24, mode="same") - np.convolve(x, np.ones(400) / 400, mode="same")
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    return x * shape * 0.5


A4 = 440.0
def hz(semi):  # semitones from A4
    return A4 * 2 ** (semi / 12)


def SFX(name):
    """Meaning-tied cues. Gains are pre-balanced to sit well below the voice."""
    if name == "move":        # meaningful transformation
        return noise_swell(0.8) * db(-26)
    if name == "accent":      # important result
        return (tone(hz(7), 1.6, ((1, 1), (2, .35), (3, .12)), decay=0.45) * db(-24))
    if name == "anticipate":  # quiet anticipation before a prediction
        s = tone(hz(-12), 2.5, ((1, 1), (2, .2))) * env(int(2.5 * SR), 1.2, 1.2)
        return s * db(-32)
    if name == "release":     # after a solved problem: gentle major arpeggio
        out = np.zeros(int(2.2 * SR), np.float32)
        for i, s in enumerate((0, 4, 7, 12)):
            nt = tone(hz(s - 9), 1.6, ((1, 1), (2, .25)), decay=0.5)
            o = int(i * 0.12 * SR)
            out[o:o + len(nt)] += nt
        return out * db(-27)
    if name == "motif":       # chapter-transition motif: rising 3-note figure
        out = np.zeros(int(2.6 * SR), np.float32)
        for i, s in enumerate((-9, -2, 3)):
            nt = tone(hz(s), 1.8, ((1, 1), (2, .3), (3, .1)), decay=0.6)
            o = int(i * 0.28 * SR)
            out[o:o + len(nt)] += nt
        return out * db(-22)
    if name == "wrong":       # soft low 'thud' marking a flawed step (not a buzzer)
        return tone(hz(-26), 0.5, ((1, 1), (2, .4)), decay=0.12) * db(-22)
    raise KeyError(name)


def music_bed(n):
    """Sparse pad: Am7 – Fmaj7 – Cmaj7 – G6, 8 s per chord, slow attack/release."""
    chords = [(-12, -5, 0, 3), (-16, -9, -5, 0), (-21, -14, -9, -5), (-14, -10, -7, -2)]
    seg = 8 * SR
    out = np.zeros(n + seg, np.float32)
    t = np.arange(seg + SR) / SR
    for i in range(0, n, seg):
        ch = chords[(i // seg) % 4]
        s = np.zeros(len(t), np.float32)
        for k, semi in enumerate(ch):
            f = hz(semi - 12)
            lfo = 1 + 0.004 * np.sin(2 * np.pi * (0.11 + 0.03 * k) * t)
            s += np.sin(2 * np.pi * f * t * lfo) + 0.18 * np.sin(4 * np.pi * f * t)
        s *= env(len(t), 2.5, 2.5) / 4
        end = min(len(out), i + len(s))
        out[i:end] += s[:end - i]
    return out[:n] * db(-6)


def build(timeline_path, out_wav):
    tl = json.load(open(timeline_path))
    n = int((tl["duration"] + 0.5) * SR)
    voice = np.zeros(n, np.float32)
    fx = np.zeros(n, np.float32)
    for e in tl["events"]:
        i = int(e["t"] * SR)
        if e["kind"] == "voice":
            v = read_wav(e["path"])
            voice[i:i + len(v)] += v[:max(0, n - i)]
        elif e["kind"] == "sfx":
            s = SFX(e["name"]) * db(e.get("gain_db", 0))
            fx[i:i + len(s)] += s[:max(0, n - i)]
    # music state gain curve
    target = np.full(n, db(C.MUSIC_DB_ALONE), np.float32)
    state_gain = {"on": db(C.MUSIC_DB_ALONE), "low": db(C.MUSIC_DB_ALONE - 8), "off": 0.0}
    states = [(0.0, "on")] + [(e["t"], e["state"]) for e in tl["events"] if e["kind"] == "music"]
    for (t0, s), nxt in zip(states, states[1:] + [(tl["duration"] + 1, None)]):
        target[int(t0 * SR):int(nxt[0] * SR)] = state_gain[s]
    # voice sidechain: envelope follower -> duck to MUSIC_DB_UNDER_VOICE
    win = int(0.25 * SR)
    venv = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, mode="same"))
    speaking = (venv > 0.01).astype(np.float32)
    speaking = np.convolve(speaking, np.ones(int(0.4 * SR)) / int(0.4 * SR), mode="same")
    duck = 1 - speaking * (1 - db(C.MUSIC_DB_UNDER_VOICE - C.MUSIC_DB_ALONE))
    gain = np.convolve(target, np.ones(int(0.6 * SR)) / int(0.6 * SR), mode="same") * duck
    mus = music_bed(n) * gain
    # stereo: voice centred; music slightly widened by a 9 ms Haas offset (mono-safe at this level)
    off = int(0.009 * SR)
    musR = np.concatenate([np.zeros(off, np.float32), mus[:-off]])
    L = voice + fx + mus
    R = voice + fx + 0.85 * musR + 0.15 * mus
    st = np.stack([L, R], axis=1)
    pre = out_wav + ".pre.wav"
    _write(pre, st)
    loudnorm(pre, out_wav)
    os.remove(pre)


def _write(path, st):
    st = np.clip(st, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())


def loudnorm(src, dst):
    f = f"loudnorm=I={C.TARGET_LUFS}:TP={C.TARGET_TP - 0.6}:LRA=11"  # headroom for AAC overshoot
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af", f + ":print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    f2 = (f + f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-af", f2,
                    "-ar", str(SR), dst], check=True)


def measure(path):
    """Return (integrated LUFS, true peak dBTP) via ffmpeg ebur128."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    s = r[r.rindex("Summary:"):]
    I = float(s.split("I:")[1].split("LUFS")[0])
    TP = float(s.split("Peak:")[1].split("dBFS")[0])
    return I, TP


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
    print(measure(sys.argv[2]))
