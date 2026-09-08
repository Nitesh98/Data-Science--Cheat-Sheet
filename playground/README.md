# Playground

This folder is a safe space to experiment while learning Claude Code and Python.
Nothing here is "official" — break things, rewrite things, delete things.

## Try it yourself

Run the example:

```bash
python3 playground/hello.py
```

Then try asking Claude things like:

- "Add a function to `hello.py` that adds two numbers, with a quick test."
- "Create a new script in `playground/` that reads one of the cheat-sheet PDFs and lists its filenames."
- "Explain what a Python function is, using `hello.py` as the example."
- "Set up a `requirements.txt` for a small data analysis project using pandas."

## The basic workflow, every time

1. **Ask** for what you want in plain English (a feature, a fix, an explanation).
2. Claude **reads/writes files and runs commands** to do it — you'll see each step.
3. **Check the result** — run the code yourself, or ask Claude to run it and show output.
4. When you're happy, changes get **committed** (saved to git history) and **pushed**
   (uploaded to GitHub) — Claude handles this on request, or automatically at the
   end of a task depending on how this session is set up.

## Good beginner habits

- Small steps: ask for one thing at a time rather than "build me an entire app."
- Ask "why" freely — "why did you write it this way?" is a completely normal question.
- If something breaks, paste the error back and ask what it means — that's the
  fastest way to learn to read errors.
