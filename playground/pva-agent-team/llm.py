"""
One agent loop, two ways to reach Claude:

  * If the official `anthropic` SDK is installed (`pip install anthropic`) we use it.
    -> This is what you'll run on your own laptop.
  * Otherwise we send the SAME request with Python's built-in urllib.
    -> Only because the Claude Code sandbox can't pip install. Same endpoint,
       same JSON, same loop -- see ../agent-from-scratch/ for the walk-through.

Either way messages are plain dicts, so the loop below doesn't care which one ran.
"""
import json
import os
import urllib.error
import urllib.request

import config
import tools

try:
    import anthropic
    _client = anthropic.Anthropic()          # reads ANTHROPIC_API_KEY
    BACKEND = "anthropic SDK"
except ImportError:
    _client = None
    BACKEND = "urllib (sandbox fallback)"


def _call(system, messages, tool_defs, effort):
    body = dict(model=config.MODEL, max_tokens=config.MAX_TOKENS, system=system,
                messages=messages, tools=tool_defs, output_config={"effort": effort})
    if _client is not None:
        return _client.messages.create(**body).to_dict()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), method="POST",
        headers={"content-type": "application/json", "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API error {e.code}: {e.read().decode()}") from e


def run_agent(name, system, task, tool_names, submit_tool=None, effort="high", log=print):
    """
    The agent loop: ask Claude -> run the tools it asks for -> send results back -> repeat.

    submit_tool: an optional extra tool ({"name", "description", "input_schema"}) that the
    agent calls to hand in structured output (e.g. the Writer's draft). We don't "run" it --
    we just keep its input and tell the agent it was received.

    Returns (final_text, submitted_input_or_None).
    """
    tool_defs = tools.tool_definitions(tool_names) + ([submit_tool] if submit_tool else [])
    messages = [{"role": "user", "content": task}]
    submitted = None

    for turn in range(config.MAX_AGENT_TURNS):
        resp = _call(system, messages, tool_defs, effort)
        stop = resp["stop_reason"]
        content = resp["content"]
        messages.append({"role": "assistant", "content": content})   # keep ALL blocks (incl. thinking)

        if stop == "refusal":
            return f"[{name} declined this request]", submitted
        if stop == "max_tokens":
            raise RuntimeError(f"{name} hit max_tokens -- raise config.MAX_TOKENS")
        if stop != "tool_use":                                        # end_turn: agent is done
            text = "\n".join(b["text"] for b in content if b["type"] == "text").strip()
            return text, submitted

        results = []
        for b in content:
            if b["type"] != "tool_use":
                continue
            if submit_tool and b["name"] == submit_tool["name"]:
                submitted = b["input"]
                log(f"    [{name}] submitted {b['name']}")
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": "Received."})
                continue
            log(f"    [{name}] -> {b['name']}({json.dumps(b['input'])[:120]})")
            out, is_err = tools.execute(b["name"], b["input"])
            results.append({"type": "tool_result", "tool_use_id": b["id"], "content": out, "is_error": is_err})
        messages.append({"role": "user", "content": results})           # all results in ONE message

    raise RuntimeError(f"{name} did not finish within {config.MAX_AGENT_TURNS} turns")
