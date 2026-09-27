"""
Muse's hands. Two kinds of tools:

  * CLIENT tools (below) -- Python functions WE run: memory, tasks, goals, notes, maths, time.
  * SERVER tools -- web_search / web_fetch, which Anthropic runs for us; we just declare them.

Safety rails:
  * Every tool input is validated against its schema before running (inputs stream in
    eagerly, so a truncated or malformed input must be caught here, not trusted).
  * Tools in NEEDS_APPROVAL ask the human first; a "no" goes back to Claude as the result.
  * In incognito mode nothing is written to disk -- write tools say so instead.
"""
import ast
import json
import operator
import re
from datetime import datetime

from memory import CATEGORIES

_PRIORITY = ["low", "normal", "high"]

CLIENT_TOOLS = [
    {"name": "remember",
     "description": ("Save a durable fact about the user to long-term memory: who they are, preferences, "
                     "relationships, goals, health, work, important dates. Call it when the user shares "
                     "something worth knowing next week, or explicitly asks you to remember. Write the fact "
                     "as one self-contained sentence in the third person ('The user is vegetarian'). Do NOT "
                     "save small talk, one-off requests, or anything the user asked you to keep off the record."),
     "input_schema": {"type": "object", "properties": {
         "content": {"type": "string"},
         "category": {"type": "string", "enum": CATEGORIES},
         "importance": {"type": "integer", "description": "1 = trivia ... 5 = core identity / safety-critical"}},
         "required": ["content", "category", "importance"]}},
    {"name": "recall",
     "description": ("Search long-term memory for facts about the user. The most relevant facts are already "
                     "in <muse_context> each turn; call this only to dig for something not shown there."),
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]}},
    {"name": "forget",
     "description": ("Remove a fact from memory by id -- when the user asks you to forget it, or it is now "
                     "wrong (then save the corrected fact with `remember`). The user must approve."),
     "input_schema": {"type": "object", "properties": {
         "fact_id": {"type": "integer"}, "reason": {"type": "string"}}, "required": ["fact_id", "reason"]}},
    {"name": "add_task",
     "description": ("Add a to-do or reminder. `due` is an ISO date or datetime in the user's local time "
                     "(resolve 'tomorrow', 'next Friday' using the date in <muse_context>)."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"}, "due": {"type": "string"},
         "priority": {"type": "string", "enum": _PRIORITY}, "notes": {"type": "string"}},
         "required": ["title"]}},
    {"name": "list_tasks",
     "description": "List tasks. status: open (default), done, or all. Optionally filter by goal name.",
     "input_schema": {"type": "object", "properties": {
         "status": {"type": "string", "enum": ["open", "done", "all"]}, "goal": {"type": "string"}}}},
    {"name": "complete_task",
     "description": "Mark a task done by id.",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}},
    {"name": "create_plan",
     "description": ("Turn a goal into a concrete, dated action plan: saves the goal to memory and creates one "
                     "task per step, all linked to the goal. Use for multi-week aims ('run a 10k by March', "
                     "'prepare for my promotion case'). Make steps small, specific and realistically dated."),
     "input_schema": {"type": "object", "properties": {
         "goal": {"type": "string"},
         "steps": {"type": "array", "items": {"type": "object", "properties": {
             "title": {"type": "string"}, "due": {"type": "string"}}, "required": ["title"]}}},
         "required": ["goal", "steps"]}},
    {"name": "save_note",
     "description": ("Save longer writing for later: research findings (with source URLs), meeting notes, a "
                     "journal entry, a draft. Use `remember` for short facts instead."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"}, "body": {"type": "string"}, "tags": {"type": "string"}},
         "required": ["title", "body"]}},
    {"name": "search_notes",
     "description": "Keyword-search the user's saved notes.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "calculate",
     "description": ("Evaluate an arithmetic expression exactly (+ - * / // % ** and parentheses). Use it for "
                     "any money, date-span, unit or percentage maths instead of doing it in your head."),
     "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}},
                      "required": ["expression"]}},
]

SERVER_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 5},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 5},
]

NEEDS_APPROVAL = {"forget"}
WRITES = {"remember", "forget", "add_task", "complete_task", "create_plan", "save_note"}

_TYPES = {"string": str, "integer": int, "array": list, "object": dict}


def tool_definitions(eager_streaming):
    tools = [dict(t, eager_input_streaming=True) if eager_streaming else t for t in CLIENT_TOOLS]
    return tools + SERVER_TOOLS


def validate(args, schema):
    """Minimal JSON-schema check: required keys present, declared types and enums respected."""
    if not isinstance(args, dict):
        return "input is not an object"
    for key in schema.get("required", []):
        if key not in args:
            return f"missing required field '{key}'"
    for key, val in args.items():
        spec = schema.get("properties", {}).get(key)
        if spec is None:
            continue
        want = _TYPES.get(spec.get("type"))
        if want and (not isinstance(val, want) or (want is int and isinstance(val, bool))):
            return f"field '{key}' should be {spec['type']}"
        if "enum" in spec and val not in spec["enum"]:
            return f"field '{key}' must be one of {spec['enum']}"
        if spec.get("type") == "array" and "items" in spec:
            for item in val:
                err = validate(item, spec["items"])
                if err:
                    return f"{key}[]: {err}"
    return None


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
        ast.USub: operator.neg, ast.UAdd: operator.pos}


def calculate(expression):
    """Safe arithmetic: walks the syntax tree and only allows numbers and the operators above."""
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("exponent too large")
            return _OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError("only numbers and + - * / // % ** ( ) are allowed")
    return ev(ast.parse(expression, mode="eval").body)


_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_SECRET = re.compile(r"\b(password|passcode|passwd|pwd|cvv|cvc|pin|otp)\b\s*(is|:|=)?\s*\S+", re.I)


def _luhn(digits):
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def contains_secret(text):
    """True if text looks like it holds a payment card number, a password, PIN, CVV or OTP."""
    for m in _CARD.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn(digits):
            return True
    return bool(_SECRET.search(text))


def _valid_date(s):
    try:
        datetime.fromisoformat(s)
        return True
    except ValueError:
        return False


class Toolbox:
    def __init__(self, memory, incognito=False):
        self.mem = memory
        self.incognito = incognito
        self._schemas = {t["name"]: t["input_schema"] for t in CLIENT_TOOLS}

    def run(self, name, args, approve=lambda name, args: True):
        """Run one client tool. Returns (result_text, is_error)."""
        if name not in self._schemas:
            return f"unknown tool '{name}'", True
        err = validate(args, self._schemas[name])
        if err:
            return json.dumps({"INVALID_INPUT": err}), True
        if name in WRITES and contains_secret(json.dumps(args, ensure_ascii=False)):
            return ("Blocked: this looks like a card number, password, PIN, CVV or OTP. Muse never stores "
                    "those. Nothing was saved; tell the user."), True
        if self.incognito and name in WRITES:
            return "Incognito mode is on: nothing was saved. Tell the user if it matters.", False
        if name in NEEDS_APPROVAL and not approve(name, args):
            return "The user declined this action. Do not retry it; ask what they would prefer.", True
        try:
            return getattr(self, "_" + name)(**args), False
        except Exception as e:                       # a tool bug should become a message, not a crash
            return f"{type(e).__name__}: {e}", True

    def _remember(self, content, category, importance):
        fid, how = self.mem.remember(content, category, importance)
        return f"Memory #{fid} {how}."

    def _recall(self, query, limit=8):
        hits = self.mem.recall(query, limit)
        return "\n".join(f"#{f['id']} [{f['category']}] {f['content']}" for f in hits) or "No matching memories."

    def _forget(self, fact_id, reason):
        return f"Forgot memory #{fact_id}." if self.mem.forget(fact_id) else f"No active memory #{fact_id}."

    def _add_task(self, title, due=None, priority="normal", notes=""):
        if due and not _valid_date(due):
            return f"'{due}' is not an ISO date (YYYY-MM-DD or YYYY-MM-DDTHH:MM). Resolve it and retry."
        return f"Task #{self.mem.add_task(title, due, priority, notes)} added."

    def _list_tasks(self, status="open", goal=None):
        rows = self.mem.tasks(status, goal)
        return "\n".join(
            f"#{t['id']} [{t['status']}] {t['title']}" + (f" (due {t['due']})" if t["due"] else "")
            + (f" <{t['priority']}>" if t["priority"] != "normal" else "") + (f" goal: {t['goal']}" if t["goal"] else "")
            for t in rows) or "No tasks."

    def _complete_task(self, task_id):
        return f"Task #{task_id} done." if self.mem.complete_task(task_id) else f"No open task #{task_id}."

    def _create_plan(self, goal, steps):
        bad = [s["due"] for s in steps if s.get("due") and not _valid_date(s["due"])]
        if bad:
            return f"These dues are not ISO dates: {bad}. Fix and retry; nothing was saved."
        self.mem.remember(f"Goal: {goal}", "goal", 4)
        ids = [self.mem.add_task(s["title"], s.get("due"), "normal", "", goal) for s in steps]
        return f"Goal saved; created tasks {', '.join('#%d' % i for i in ids)}."

    def _save_note(self, title, body, tags=""):
        return f"Note #{self.mem.save_note(title, body, tags)} saved."

    def _search_notes(self, query):
        hits = self.mem.search_notes(query)
        return "\n\n".join(f"#{n['id']} {n['title']} ({n['created_at'][:10]})\n{n['body']}" for n in hits) \
            or "No matching notes."

    def _calculate(self, expression):
        return str(calculate(expression))
