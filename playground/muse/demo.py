"""
A stand-in for Claude so you can try Muse's app without an API key: `python3 web.py --demo`.

Replies are SCRIPTED (picked by keywords in your message), but everything around them is
real: tool calls hit the real memory/tasks/notes, approval prompts really block, and the
end-of-session reflection really writes an episode. The app shows a "demo" badge throughout.
"""
import json
import re
import time
from datetime import date, timedelta

GENERIC = ("This is demo mode, so my replies are scripted. Try one of these:\n"
           "- *I'm training for a 10k in December and I'm vegetarian*\n"
           "- *make me a plan*\n- *what should I eat before my run?*\n"
           "- *done with today's run*\n- *forget that I'm vegetarian*\n\n"
           "Set `ANTHROPIC_API_KEY` and start without `--demo` to talk to the real Muse.")


def _day(iso):
    return date.fromisoformat(iso[:10]).strftime("%a %d %b") if iso else ""


def _text(t):
    return {"type": "text", "text": t}


def _tool(name, args):
    return {"type": "tool_use", "id": f"demo_{name}_{time.time_ns()}", "name": name, "input": args}


def _reply(*blocks, stop="end_turn"):
    return {"content": list(blocks), "stop_reason": stop}


class DemoClaude:
    def __init__(self, memory, delay=0.012):
        self.mem = memory
        self.delay = delay
        self.queue = []

    def _script(self, msg):
        m = msg.lower()
        if re.search(r"\bforget\b", m):
            word = next((w for w in re.findall(r"[a-z]+", m) if len(w) > 4 and w not in ("forget", "about")), "")
            fact = next((f for f in self.mem.facts() if word and word in f["content"].lower()), None)
            if not fact:
                return [_reply(_text("I couldn't find a memory matching that. Open the Memory tab to see everything I know."))]
            return [_reply(_text("Understood."), _tool("forget", {"fact_id": fact["id"], "reason": "The user asked to forget it"}),
                           stop="tool_use"),
                    _reply(_text("Done. If you declined, nothing changed."))]
        if re.search(r"\b(done|finished|completed)\b", m):
            task = next(iter(self.mem.tasks()), None)
            if not task:
                return [_reply(_text("Nothing open on your list. Nice."))]
            nxt = self.mem.tasks()[1:2]
            after = f" Next up: **{nxt[0]['title']}**" + (f" on {_day(nxt[0]['due'])}." if nxt[0]["due"] else ".") if nxt else ""
            return [_reply(_text("Nice work!"), _tool("complete_task", {"task_id": task["id"]}), stop="tool_use"),
                    _reply(_text(f"Marked **{task['title']}** done.{after}"))]
        if re.search(r"\b(list|this week|to-?do|tasks)\b", m):
            open_tasks = self.mem.tasks()
            if not open_tasks:
                summary = "Your list is empty. Tell me a goal and I'll turn it into a dated plan."
            else:
                lines = "\n".join(f"- **{t['title']}**" + (f" · {_day(t['due'])}" if t["due"] else "") for t in open_tasks[:5])
                summary = f"You have {len(open_tasks)} open task{'s' if len(open_tasks) != 1 else ''}. Coming up:\n{lines}"
            return [_reply(_tool("list_tasks", {"status": "open"}), stop="tool_use"), _reply(_text(summary))]
        if re.search(r"\b(plan|schedule)\b", m):
            d = date.today()
            nxt = [d + timedelta(days=(1 - d.weekday()) % 7 or 7)]          # next Tuesday
            for gap in (2, 2, 7, 21, 28):
                nxt.append(nxt[-1] + timedelta(days=gap))
            titles = ["Easy 3k run", "Easy 3k run", "4k run + stretching", "5k steady run", "7k long run", "10k time trial"]
            steps = [{"title": t, "due": x.isoformat()} for t, x in zip(titles, nxt)]
            return [_reply(_text("On it."), _tool("create_plan", {"goal": "Run a 10k in December", "steps": steps}),
                           stop="tool_use"),
                    _reply(_text(f"Done: **6 dated runs**, building from an easy 3k to a 10k time trial on "
                                 f"{nxt[-1]:%d %b}. They're in your **Tasks** tab. I'll flag anything you miss."))]
        if re.search(r"\b(10k|training|marathon|vegetarian)\b", m):
            blocks = [_text("Two good things to know.")]
            if "10k" in m or "training" in m:
                blocks.append(_tool("remember", {"content": "The user is training for a 10k race in December",
                                                 "category": "goal", "importance": 4}))
            if "vegetarian" in m:
                blocks.append(_tool("remember", {"content": "The user is vegetarian", "category": "preference",
                                                 "importance": 4}))
            return [_reply(*blocks, stop="tool_use"),
                    _reply(_text("Noted. Want me to turn the 10k into a **week-by-week plan** with dated runs?"))]
        if re.search(r"\b(eat|food|snack|meal)\b", m):
            veg = any("vegetarian" in f["content"].lower() for f in self.mem.facts())
            return [_reply(_text(
                ("Since you're vegetarian, try" if veg else "Try") + " one of these 60–90 minutes before:\n"
                "- a banana with a spoon of peanut butter\n- toast with honey\n- a small bowl of poha\n\n"
                "Keep it light and sip water. Want a post-run recovery meal too?"))]
        return [_reply(_text(GENERIC))]

    def __call__(self, params, on_text=None):
        if "format" in params.get("output_config", {}):        # end-of-session reflection
            return _reply(_text(json.dumps({
                "summary": "Demo session: talked about training for a December 10k and pre-run food.",
                "new_facts": [], "outdated_fact_ids": []})))
        last = params["messages"][-1]
        if last["role"] == "user" and any(b.get("type") == "text" for b in last["content"]):
            self.queue = self._script(last["content"][-1]["text"])
        resp = self.queue.pop(0) if self.queue else _reply(_text("…"))
        for b in resp["content"]:
            if b["type"] == "text" and on_text:
                for word in re.findall(r"\S+\s*", b["text"]):
                    on_text(word)
                    time.sleep(self.delay)
        return resp
