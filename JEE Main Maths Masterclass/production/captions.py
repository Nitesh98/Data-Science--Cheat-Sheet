"""SRT/VTT captions and timecoded cue sheets from timeline JSON.

Captions are the exact narration text of each synthesized clip, placed at the
clip's real start time; long clips are split at word boundaries in proportion
to character count (each piece <= 2 lines of <= 42 characters).
"""
import json, textwrap


def ts(t, sep=","):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d}{sep}{ms % 1000:03d}"


def cues(events, offset=0.0, width=42):
    out = []
    for e in events:
        if e["kind"] != "voice":
            continue
        lines = textwrap.wrap(e["text"], width)
        groups = [lines[i:i + 2] for i in range(0, len(lines), 2)]
        total = sum(len(" ".join(g)) for g in groups)
        t = e["t"] + offset
        for g in groups:
            d = e["dur"] * len(" ".join(g)) / total
            out.append((t, t + d, "\n".join(g)))
            t += d
    return out


def write_srt(cs, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, txt) in enumerate(cs, 1):
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")


def write_vtt(cs, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for a, b, txt in cs:
            f.write(f"{ts(a, '.')} --> {ts(b, '.')}\n{txt}\n\n")


def cue_sheet(events, path, offset=0.0, title=""):
    """Human-readable timecoded audio cue sheet (Markdown)."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Audio cue sheet — {title}\n\n| Time | Track | Cue | Detail |\n|---|---|---|---|\n")
        for e in events:
            t = ts(e["t"] + offset, ".")[:-1]
            if e["kind"] == "voice":
                f.write(f"| {t} | VO | line ({e['dur']:.1f}s) | {e['text']} |\n")
            elif e["kind"] == "sfx":
                f.write(f"| {t} | SFX | {e['name']} | |\n")
            elif e["kind"] == "music":
                f.write(f"| {t} | MUSIC | {e['state']} | |\n")
            elif e["kind"] == "section":
                f.write(f"| {t} | NAV | section {e['id']} | {e['title']} |\n")
