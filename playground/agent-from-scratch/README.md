# Building an Agent from Scratch

A hands-on walkthrough of how AI agents actually work, using the real
Claude API. No frameworks, no magic — about 150 lines of Python you can
read top to bottom.

## The core idea, before any code

A single call to an LLM answers using only what it already knows. An
**agent** can also take *actions*: it asks your program to run a **tool**
(a function you wrote), sees the real result, and keeps reasoning with that
new information. That "decide → act → observe → repeat" cycle is called
**the agent loop**, and it's the same idea whether the tool is a toy
calculator (this exercise) or something that edits a codebase, queries a
production database, or books a flight.

The model **never runs code itself** — it has no hands. All it can do is
say, in a structured format, "please run `get_current_time` for me." Your
program is the one that actually executes it and reports back. This
separation is exactly why agents are safe(r) to build: you decide what
tools exist and what they're allowed to touch.

## What's in here

| File | Purpose |
|---|---|
| `agent.py` | **The real lesson.** Uses the official `anthropic` Python SDK — this is what you'd actually write on your own machine. |
| `agent_sandbox_demo.py` | A stdlib-only (`urllib`) reimplementation of the *exact same loop*, needed only because this Claude Code sandbox can reach `api.anthropic.com` but can't `pip install` the SDK. It exists purely so we can watch it run live in this session — not a pattern to copy elsewhere. |

## The loop, in plain English

1. You send Claude the conversation so far, plus a list of tools it's allowed to use.
2. Claude replies either with a plain answer, or a request to call a tool.
3. **Your code** runs that tool and gets a real result — Claude doesn't see this step happen, it only sees what you send back.
4. You send the result back to Claude as a "tool result."
5. Claude reads it and either answers, or asks for another tool call.

Repeat 2–5 until Claude gives a plain answer. That's the entire mechanism —
`while True: ... if done: break`.

## Running it

**On your own machine** (recommended — this is the one to actually run):

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...    # get a key at console.anthropic.com
python3 agent.py
```

**In this sandbox** (to see it work right now, without installing anything):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python3 agent_sandbox_demo.py "What's 47 * (12 + 8), and is that bigger than 1000?"
```

Either way, you need an API key from [console.anthropic.com](https://console.anthropic.com/) —
**never paste a real API key into a chat conversation** (including this one) if you can avoid it;
run it in your own terminal where the key stays local to your machine. If you
do want to test it live in this session, know that it becomes part of the
conversation transcript.

## Two tools, on purpose kept simple

- `get_current_time` — no inputs, just proves the round-trip works.
- `calculate` — evaluates arithmetic **without using Python's `eval()`**.
  This is a real, deliberate security choice worth understanding: Claude's
  tool-call arguments are the model's own generated text — you should treat
  them as untrusted input, the same way you'd treat text a random user
  typed into a form. `eval("2+2")` looks harmless, but `eval()` runs *any*
  Python expression, including `__import__('os').system(...)`. Try
  swapping `_safe_eval` for `eval()` and asking the agent something that
  tricks it into passing a malicious expression — then look at why the
  AST-walking version can't be tricked the same way (it only ever
  recognizes arithmetic nodes; anything else raises `ValueError` before
  it's ever executed).

## Things to try next, in order of difficulty

1. Add a third tool — e.g. `word_count(text: str)` — and watch Claude
   decide on its own when to call it.
2. Ask a question that needs **two tool calls to answer** (e.g. "what's the
   time, and what's that hour number squared?") and watch the loop run
   twice.
3. Break something on purpose: return `is_error: true` from a tool and see
   how Claude reacts to a failed tool call.
4. Once this clicks, look at the **Tool Runner** (`client.beta.messages.tool_runner`
   in the SDK) — it automates this exact loop so you don't hand-write it
   for every project. Understanding the manual version first is what makes
   the automated one make sense.
