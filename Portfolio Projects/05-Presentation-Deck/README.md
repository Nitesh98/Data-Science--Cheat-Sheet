# Presentation Deck

A 10-slide walkthrough of the four portfolio case studies — for an
interview, a promotion packet, or a portfolio review.

## ⚠️ Please open and check this before relying on it

This deck was **built without being able to visually preview it**. The
sandbox this was built in blocks `npm install`/`pip install` (so
`pptxgenjs`/`python-pptx` aren't available — see below), and its
LibreOffice install turned out to be broken too (it can't even open a
plain `.txt` file, unrelated to anything in this deck). That means the
usual visual QA pass — rendering every slide to an image and eyeballing
it for overlap or text overflow — could not be run here.

What **was** verified: the file is a structurally valid `.pptx` (zip
integrity check passes, and all 31 internal XML parts parse cleanly
against the OOXML schema). What was **not** verified: how it actually
looks. Please open `Portfolio_Overview.pptx` in real PowerPoint, Google
Slides, or Keynote and check for text overflow or spacing issues before
using it — and tell me what you see so I can fix anything that's off.

## Why this is hand-built OOXML instead of the usual tool

The standard way to build a deck (`pptxgenjs`, or editing an existing
`.pptx` via `python-pptx`) needs a package install, and this sandbox has
no `npm`/`pip` registry access — the same constraint that forced Projects
01–04 into pure-Python-stdlib. `pptx_builder.py` is a small, dependency-free
`.pptx` writer (just `zipfile` + string templates for the OOXML parts);
`build_deck.py` uses it to lay out all 10 slides. Charts are drawn as
proportionally-sized rectangles rather than native interactive PowerPoint
charts, for the same reason — hand-writing the OOXML chart-part format
correctly is far more error-prone than a plain shape, for no benefit in a
static deck.

## What's in here

| File | Purpose |
|---|---|
| `pptx_builder.py` | Minimal stdlib `.pptx` writer: text boxes, rectangles, ellipses, a bar-chart-from-shapes helper. |
| `build_deck.py` | The deck's actual content and layout. Every number in it is transcribed from an already-computed, committed file in Projects 01–04 (cited in a comment above each slide) — not re-derived here. |
| `Portfolio_Overview.pptx` | The output. |

## Run it yourself

```bash
python3 build_deck.py   # -> Portfolio_Overview.pptx
```

## Palette

"Midnight Executive" — navy (`1E2761`) / ice blue (`CADCFC`) / white —
a corporate, analytics-appropriate palette for a hiring-panel audience,
sandwiched (dark title/closing, light content slides) per standard deck
design practice.
