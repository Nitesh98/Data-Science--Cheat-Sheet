# JEE Main Mathematics — One-Shot Visual Revision Masterclass

Status: **in production**. Only the representative sequence (C01.7, graph
transformations) has been rendered. Nothing listed below as "planned" exists yet.

## What is here

| Path | What it is | Status |
|---|---|---|
| `docs/syllabus/SOURCE.md` | Which NTA syllabus is used, its URLs, and what could not be verified | done (official PDF not yet diffed) |
| `docs/syllabus/JEE_MAIN_2026_MATHS_TRANSCRIPTION.md` | Unit-by-unit syllabus text | transcribed, unverified |
| `docs/coverage_data.py` → `coverage_matrix.csv/.md` | 116 syllabus + 4 prerequisite rows → chapters/sections | done; timestamps fill in after rendering |
| `registry/registry.py`, `registry/verify.py` → `verify/REPORT.md` | Formula/example registry with sympy checks | 11 entries (C00, C01.7); rest planned |
| `production/` | Manim + ffmpeg pipeline (see below) | working |
| `production/scenes/c01_7_transformations.py` | Representative sequence | rendered |
| `renders/` (gitignored) | Videos, audio, captions, QA reports | local only |

## Pipeline

* `style.py` — semantic colours (teal input, amber output, violet parameter,
  coral restriction, yellow focus, green verified), Inter + LaTeX, equal-scale axes,
  progress bar, panels, countdown.
* `narrated.py` — `NarratedScene.say(text, *animations)`: every caption chunk is
  synthesized first, and the scene holds until the *measured* narration ends.
  All voice clips, sound cues, music states and section markers go to a timeline JSON.
* `tts.py` — cached narration. Backend set in `config.py` (`espeak-ng` now;
  `piper` or `recorded` for a better voice; changing it re-times every scene).
* `audio_mix.py` — original synthesized music bed and effects, voice sidechain
  ducking, music off during dense reasoning, two-pass loudnorm to −14 LUFS / ≤ −1 dBTP.
* `captions.py` — SRT/VTT from the real clip times, plus a timecoded cue sheet.
* `build.py` — render → mix → mux → 1080p copy → captions → automated QA JSON
  (resolution, fps, duration, audio stream, loudness, black frames).

## Reproduce

Requirements: Python 3.11+, `pip install manim==0.22.0 sympy`, a TeX Live install
with `dvisvgm`, FFmpeg, sox, espeak-ng, the Inter font.

```
cd production
python build.py scenes/c01_7_transformations.py C01_7_Transformations --preview   # 720p15 draft
python build.py scenes/c01_7_transformations.py C01_7_Transformations             # 3840x2160@30 + 1080p
python ../registry/verify.py
python ../docs/build_coverage.py
```

## Known limitations (honest list)

* Narration is **espeak-ng Hindi** (Hinglish: Devanagari Hindi + English maths terms).
  It is intelligible but robotic. It is a placeholder until a neural Hindi voice or a
  human recording is supplied. Audio has been metered, not listened to by a human.
* The official NTA PDF could not be downloaded from the build environment; see
  `docs/syllabus/SOURCE.md`.
* No weightage or "most repeated" claims are made anywhere.
