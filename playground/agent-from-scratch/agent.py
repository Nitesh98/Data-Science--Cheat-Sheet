"""
A minimal "agent" built from scratch with the Claude API, using the
official `anthropic` Python SDK. This is the REAL version -- run this on
your own machine (this sandbox can't `pip install`, see README.md).

    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...      # get one at console.anthropic.com
    python3 agent.py

--------------------------------------------------------------------------
WHAT MAKES THIS AN "AGENT" AND NOT JUST A CHATBOT?
--------------------------------------------------------------------------
A single call to Claude answers a question using only what it already
knows. An AGENT can also take ACTIONS -- it decides to call a TOOL (a
function you wrote), sees the real result, and keeps going until it has
a real answer. That decide -> act -> observe -> repeat cycle is "the
agent loop", and it's the same idea whether the tool is a calculator (as
below) or something that edits files, queries a database, or books a
flight.

Concretely, each round trip works like this:
  1. You send Claude the conversation + a list of tools it's allowed to use.
  2. Claude replies with either a normal answer, OR a request to run a
     tool ("tool_use") -- it does NOT run the tool itself; it can't, it
     has no hands. It just says "please run get_current_time for me".
  3. YOUR code runs that tool function and gets a real result.
  4. You send that result back to Claude as a "tool_result".
  5. Claude reads it and either answers, or asks for another tool call.
Repeat steps 2-5 until Claude gives a plain answer (stop_reason == "end_turn").
"""
import ast
import json
import operator
from datetime import datetime, timezone

import anthropic

MODEL = "claude-opus-5"


# --------------------------------------------------------------------
# STEP 1: Define the tools. Each tool needs a name, a description (Claude
# reads this to decide WHEN to use it -- be specific), and a JSON Schema
# describing its inputs.
# --------------------------------------------------------------------
TOOLS = [
    {
        "name": "calculate",
        "description": (
            "Evaluate a basic arithmetic expression (+, -, *, /, **, parentheses). "
            "Call this whenever the user asks for a calculation, instead of doing "
            "the arithmetic yourself -- it's guaranteed correct."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "e.g. '12 * (3 + 4)'",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_current_time",
        "description": "Get the current date and time in UTC. Call this whenever the user asks what time or date it is.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# --------------------------------------------------------------------
# STEP 2: Implement what each tool actually DOES. This is just regular
# Python -- there's nothing magic about a "tool", it's a function you
# already know how to write. The only new part is wiring it up below.
# --------------------------------------------------------------------
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
}


def _safe_eval(node):
    """Evaluate an arithmetic AST node. Deliberately NOT using Python's
    eval() -- Claude's output is untrusted input, and eval() on untrusted
    input can run arbitrary code. Walking a restricted AST like this only
    ever does arithmetic, nothing else, no matter what expression comes in."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def calculate(expression: str) -> str:
    try:
        result = _safe_eval(ast.parse(expression, mode="eval").body)
        return str(result)
    except Exception as e:
        return f"Error: could not evaluate '{expression}': {e}"


def get_current_time() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def execute_tool(name: str, tool_input: dict) -> str:
    """Dispatch a tool_use request to the matching Python function."""
    if name == "calculate":
        return calculate(**tool_input)
    if name == "get_current_time":
        return get_current_time()
    return f"Error: unknown tool '{name}'"


# --------------------------------------------------------------------
# STEP 3: The agent loop itself. This is the part worth reading slowly.
# --------------------------------------------------------------------
def run_agent(client: anthropic.Anthropic, user_message: str, verbose: bool = True) -> str:
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

        # Claude is done -- no more tool calls, this is the final answer.
        if response.stop_reason == "end_turn":
            return next(b.text for b in response.content if b.type == "text")

        if response.stop_reason == "tool_use":
            # A response can contain BOTH explanatory text AND tool_use
            # blocks -- print the text if there is any, for visibility.
            if verbose:
                for block in response.content:
                    if block.type == "text" and block.text.strip():
                        print(f"  [Claude, before calling a tool]: {block.text.strip()}")

            # IMPORTANT: append the assistant's full response (not just the
            # text) -- this preserves the tool_use blocks, which Claude
            # needs to see again to know which tool_result answers which call.
            messages.append({"role": "assistant", "content": response.content})

            # Claude may ask for multiple tools in one turn -- handle all
            # of them, then send all results back together in ONE message.
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if verbose:
                    print(f"  [Claude is calling]: {block.name}({json.dumps(block.input)})")
                result = execute_tool(block.name, block.input)
                if verbose:
                    print(f"  [Tool result]: {result}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,  # links this result to that exact call
                    "content": result,
                })
            messages.append({"role": "user", "content": tool_results})
            continue  # loop again -- Claude hasn't given a final answer yet

        # Anything else (max_tokens, refusal, ...) -- stop rather than loop forever.
        raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")


if __name__ == "__main__":
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    for question in [
        "What time is it right now?",
        "What's 47 * (12 + 8), and is that bigger than 1000?",
        "What's the capital of France?",  # no tool needed -- Claude just answers
    ]:
        print(f"\nUser: {question}")
        answer = run_agent(client, question)
        print(f"Agent: {answer}")
