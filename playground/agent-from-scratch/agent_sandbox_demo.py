"""
SANDBOX-ONLY WORKAROUND -- read agent.py first; that one is the real lesson.

This Claude Code sandbox has network access to api.anthropic.com but can't
`pip install` anything (no package index reachable), so the official
`anthropic` SDK isn't available here. This file re-implements the exact
same agent loop from agent.py using only Python's built-in `urllib`, purely
so we can watch it actually run inside this session. On your own machine,
use agent.py + `pip install anthropic` instead -- that's the version worth
keeping; this one exists only to work around this sandbox's limitation.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 agent_sandbox_demo.py "What's 47 * (12 + 8)?"
"""
import ast
import json
import operator
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

MODEL = "claude-opus-5"
API_URL = "https://api.anthropic.com/v1/messages"

TOOLS = [
    {
        "name": "calculate",
        "description": (
            "Evaluate a basic arithmetic expression (+, -, *, /, **, parentheses). "
            "Call this whenever the user asks for a calculation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "e.g. '12 * (3 + 4)'"}},
            "required": ["expression"],
        },
    },
    {
        "name": "get_current_time",
        "description": "Get the current date and time in UTC.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def execute_tool(name, tool_input):
    if name == "calculate":
        try:
            return str(_safe_eval(ast.parse(tool_input["expression"], mode="eval").body))
        except Exception as e:
            return f"Error: {e}"
    if name == "get_current_time":
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"Error: unknown tool '{name}'"


def call_claude(api_key: str, messages: list) -> dict:
    """The part the SDK normally does for you: build the HTTP request by
    hand. Same endpoint, same JSON body shape, same headers the SDK sends."""
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 1024,
        "tools": TOOLS,
        "messages": messages,
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API error {e.code}: {e.read().decode()}") from e


def run_agent(api_key: str, user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = call_claude(api_key, messages)
        stop_reason = response["stop_reason"]
        content = response["content"]  # list of content blocks, as plain dicts here

        if stop_reason == "end_turn":
            return next(b["text"] for b in content if b["type"] == "text")

        if stop_reason == "tool_use":
            for block in content:
                if block["type"] == "text" and block["text"].strip():
                    print(f"  [Claude, before calling a tool]: {block['text'].strip()}")

            messages.append({"role": "assistant", "content": content})

            tool_results = []
            for block in content:
                if block["type"] != "tool_use":
                    continue
                print(f"  [Claude is calling]: {block['name']}({json.dumps(block['input'])})")
                result = execute_tool(block["name"], block["input"])
                print(f"  [Tool result]: {result}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": result,
                })
            messages.append({"role": "user", "content": tool_results})
            continue

        raise RuntimeError(f"Unexpected stop_reason: {stop_reason}")


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY first, e.g.:\n  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    question = " ".join(sys.argv[1:]) or "What's 47 * (12 + 8), and is that bigger than 1000?"
    print(f"User: {question}")
    print(f"Agent: {run_agent(api_key, question)}")
