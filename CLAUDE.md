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

## Conventions

- Topic folders use Title Case with spaces (e.g. `Data Visualization`,
  `Machine Learning`) — match this if adding a new topic folder.
- `README.md` at the root indexes some of the cheat sheets with preview
  images from `Images/`.
- When adding runnable code (scripts/notebooks), prefer Python 3 and keep
  dependencies minimal; add a `requirements.txt` near the code if it needs
  third-party packages.
