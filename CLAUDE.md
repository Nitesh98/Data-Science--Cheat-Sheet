# Repo notes for Claude

## What this repo is

`Data-Science--Cheat-Sheet` is a curated **reference collection** of cheat
sheets (mostly PDFs and images) covering data science topics — Python,
Pandas, NumPy, SQL, Machine Learning, Deep Learning, Statistics, R, Excel,
Docker/Kubernetes, etc. Each top-level folder is a subject area.

This is **not** an active codebase — there's no build, test, or lint step
for the cheat-sheet content itself. Most files are static documents.

## `playground/`

A sandbox folder for the repo owner (new to Claude Code / new to
programming) to experiment: small scripts, exercises, and examples while
learning. Feel free to add to it, but keep experiments contained here
rather than scattered into the topic folders above.

## `Portfolio Projects/`

Resume/interview portfolio work for the repo owner (Manager, Analytics —
Revenue & Growth, men's footwear category at Myntra), aimed at a Senior
Manager Analytics promotion case or a Product Management pivot. Five
connected case studies (category growth diagnostic, an A/B test, a PM
PRD+roadmap, a causal DiD follow-up to project 01's confounded elasticity
finding, and a commercial-model [MP/OR/SOR] decision simulation that reuses
the DiD project's causal estimate) plus a presentation deck
(`00-Presentation-Deck/`), using **synthetic, seeded data only** — never
real company data. Python 3 standard library only (no pandas/numpy/
matplotlib/scipy/pptxgenjs/python-pptx — this environment has no
package-install access, so `svg_charts.py` and `stats_lib.py` at that
folder's root hand-implement charts and statistical tests shared across
the subprojects, and the deck is hand-built OOXML via a stdlib `.pptx`
writer). See its own `README.md` for the full map and how to run
everything.

## Privacy (the owner's standing rule; applies to every session and every agent)

Never put the repo owner's personal details (their name, email address,
phone, home address, card or bank details, ID numbers, passwords, or other
identifying information) into anything that leaves this machine: files,
commits, commit messages, PR titles or bodies, GitHub comments, screenshots,
published artifacts, web searches, or prompts to any other service. In
examples, tests, demos and sample data use neutral wording ("the user") or
obviously fictional names. The same rule goes into the prompts of any agent
built here. If existing content already contains such details, point it out
and ask before changing it.

## Conventions

- Topic folders use Title Case with spaces (e.g. `Data Visualization`,
  `Machine Learning`) — match this if adding a new topic folder.
- `README.md` at the root indexes some of the cheat sheets with preview
  images from `Images/`.
- When adding runnable code (scripts/notebooks), prefer Python 3 and keep
  dependencies minimal; add a `requirements.txt` near the code if it needs
  third-party packages.
