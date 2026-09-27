"""
Offline tests: memory, tools, and the full agent loop driven by a scripted fake Claude.

    python3 -m unittest discover -s playground/muse/tests -v
"""
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import brain  # noqa: E402
from memory import Memory, bm25  # noqa: E402
from tools import Toolbox, calculate, validate, CLIENT_TOOLS  # noqa: E402

FIXED = datetime(2026, 9, 27, 9, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))


def reply(*blocks, stop="end_turn"):
    return {"content": list(blocks), "stop_reason": stop}


def text(t):
    return {"type": "text", "text": t}


def tool(name, args, id_="t1"):
    return {"type": "tool_use", "id": id_, "name": name, "input": args}


class FakeClaude:
    """Returns scripted responses in order and records every request it was sent."""
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, params, on_text=None):
        self.requests.append(json.loads(json.dumps(params)))   # snapshot, like a real HTTP body
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        for b in r["content"]:
            if b["type"] == "text" and on_text:
                on_text(b["text"])
        return r


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.mem = Memory(":memory:")

    def test_near_duplicate_fact_is_updated_not_duplicated(self):
        a, how_a = self.mem.remember("The user prefers running in the morning", "preference", 3)
        b, how_b = self.mem.remember("The user prefers running early in the morning", "preference", 4)
        self.assertEqual((a, how_a, how_b), (b, "created", "updated"))
        self.assertEqual(self.mem.fact(a)["importance"], 4)

    def test_recall_ranks_relevant_fact_first(self):
        self.mem.remember("Sister Priya lives in Pune", "relationship", 3)
        self.mem.remember("Allergic to peanuts", "health", 5)
        self.mem.remember("Works on men's footwear analytics", "work", 3)
        hits = self.mem.recall("what snacks with peanuts are safe?")
        self.assertEqual(hits[0]["content"], "Allergic to peanuts")
        self.assertEqual(self.mem.fact(hits[0]["id"])["use_count"], 1)

    def test_forget_is_soft_and_hidden(self):
        fid, _ = self.mem.remember("Likes jazz", "preference", 2)
        self.assertTrue(self.mem.forget(fid))
        self.assertFalse(self.mem.forget(fid))
        self.assertEqual(self.mem.facts(), [])
        self.assertEqual(len(self.mem.facts(include_inactive=True)), 1)

    def test_due_tasks_split_overdue_and_today(self):
        self.mem.add_task("pay rent", due="2026-09-25")
        self.mem.add_task("call mom", due="2026-09-27T18:00")
        self.mem.add_task("someday")
        overdue, today = self.mem.due_tasks("2026-09-27")
        self.assertEqual([t["title"] for t in overdue], ["pay rent"])
        self.assertEqual([t["title"] for t in today], ["call mom"])

    def test_bm25_zero_for_unrelated(self):
        self.assertEqual(bm25("quantum", ["apples and pears"]), [0.0])


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.mem = Memory(":memory:")
        self.box = Toolbox(self.mem)

    def test_calculate_is_safe(self):
        self.assertEqual(calculate("1200 * 0.18 + (3 ** 2)"), 225.0)
        for bad in ("__import__('os')", "open('x')", "2 ** 99999"):
            with self.assertRaises(ValueError):
                calculate(bad)

    def test_validation_rejects_bad_input(self):
        schema = next(t for t in CLIENT_TOOLS if t["name"] == "remember")["input_schema"]
        self.assertIn("missing", validate({"content": "x"}, schema))
        self.assertIn("one of", validate({"content": "x", "category": "nope", "importance": 3}, schema))
        self.assertIn("integer", validate({"content": "x", "category": "other", "importance": True}, schema))
        out, err = self.box.run("remember", {"content": "x"})
        self.assertTrue(err)
        self.assertEqual(self.mem.facts(), [])

    def test_forget_needs_approval(self):
        fid, _ = self.mem.remember("Likes jazz", "preference", 2)
        out, err = self.box.run("forget", {"fact_id": fid, "reason": "asked"}, approve=lambda n, a: False)
        self.assertTrue(err)
        self.assertEqual(len(self.mem.facts()), 1)
        self.box.run("forget", {"fact_id": fid, "reason": "asked"}, approve=lambda n, a: True)
        self.assertEqual(self.mem.facts(), [])

    def test_incognito_writes_nothing(self):
        self.box.incognito = True
        out, err = self.box.run("remember", {"content": "secret", "category": "other", "importance": 3})
        self.assertIn("Incognito", out)
        self.box.run("add_task", {"title": "x"})
        self.assertEqual((self.mem.facts(), self.mem.tasks()), ([], []))

    def test_secrets_are_never_stored(self):
        for leak in ("My card is 4111 1111 1111 1111", "wifi password is hunter22", "CVV: 123"):
            out, err = self.box.run("remember", {"content": leak, "category": "other", "importance": 3})
            self.assertTrue(err, leak)
            self.assertIn("Blocked", out)
        self.box.run("save_note", {"title": "bank", "body": "account pin = 4321"})
        self.assertEqual((self.mem.facts(), self.mem.notes()), ([], []))
        # ordinary numbers are fine
        out, err = self.box.run("remember", {"content": "Ran 10000 steps; order 20260927 arrived",
                                             "category": "event", "importance": 2})
        self.assertFalse(err, out)

    def test_create_plan_links_tasks_to_goal(self):
        out, err = self.box.run("create_plan", {"goal": "Run a 10k", "steps": [
            {"title": "Run 3k", "due": "2026-10-01"}, {"title": "Run 5k", "due": "2026-10-15"}]})
        self.assertFalse(err, out)
        self.assertEqual([t["title"] for t in self.mem.tasks(goal="Run a 10k")], ["Run 3k", "Run 5k"])
        self.assertEqual(self.mem.facts()[0]["category"], "goal")

    def test_bad_due_date_saves_nothing(self):
        out, _ = self.box.run("create_plan", {"goal": "g", "steps": [{"title": "a", "due": "next friday"}]})
        self.assertIn("not ISO", out)
        self.assertEqual(self.mem.tasks(), [])


class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        self.mem = Memory(":memory:")

    def muse(self, fake):
        return brain.Muse(self.mem, call=fake, clock=lambda: FIXED)

    def test_tool_round_trip(self):
        fake = FakeClaude(
            reply(text("Noted."), tool("remember", {"content": "The user is vegetarian", "category": "preference",
                                                    "importance": 4}), stop="tool_use"),
            reply(text("I'll keep that in mind.")))
        m = self.muse(fake)
        streamed = []
        out = m.respond("I'm vegetarian", on_text=streamed.append)
        self.assertEqual(out, "Noted.\nI'll keep that in mind.")
        self.assertEqual(streamed, ["Noted.", "I'll keep that in mind."])
        self.assertEqual(self.mem.facts()[0]["content"], "The user is vegetarian")
        second = fake.requests[1]["messages"]
        self.assertEqual([x["role"] for x in second], ["user", "assistant", "user"])
        self.assertEqual(second[2]["content"][0]["tool_use_id"], "t1")

    def test_context_carries_memory_tasks_and_last_episode(self):
        self.mem.remember("Training for a 10k race", "goal", 5)
        self.mem.add_task("Buy running shoes", due="2026-09-20")
        self.mem.add_episode("2026-09-26T10:00:00+00:00", "Talked about marathon training.")
        fake = FakeClaude(reply(text("hi")), reply(text("again")))
        m = self.muse(fake)
        m.respond("hello")
        ctx = fake.requests[0]["messages"][0]["content"][0]["text"]
        for want in ("Sunday 2026-09-27 09:30", "Training for a 10k race", "OVERDUE #1 Buy running shoes",
                     "Talked about marathon training"):
            self.assertIn(want, ctx)
        m.respond("hello again")
        self.assertNotIn("last conversation", fake.requests[1]["messages"][2]["content"][0]["text"])
        # system prompt is byte-identical across turns, so the prompt cache holds
        self.assertEqual(fake.requests[0]["system"], fake.requests[1]["system"])

    def test_pause_turn_resumes_without_extra_user_message(self):
        fake = FakeClaude(reply(text("Searching…"), stop="pause_turn"), reply(text("Found it.")))
        m = self.muse(fake)
        self.assertEqual(m.respond("news?"), "Searching…\nFound it.")
        self.assertEqual([x["role"] for x in fake.requests[1]["messages"]], ["user", "assistant"])

    def test_refusal_rolls_back_the_turn(self):
        fake = FakeClaude(reply(text("partial"), stop="refusal"))
        m = self.muse(fake)
        self.assertIn("can't help", m.respond("something"))
        self.assertEqual(m.messages, [])

    def test_bad_tool_json_is_retried(self):
        fake = FakeClaude(brain.BadToolJSON("boom"), reply(text("ok")))
        self.assertEqual(self.muse(fake).respond("x"), "ok")

    def test_truncated_tool_call_never_runs(self):
        fake = FakeClaude(reply(tool("remember", {"content": "half", "category": "other", "importance": 3}),
                                stop="max_tokens"))
        with self.assertRaises(RuntimeError):
            self.muse(fake).respond("x")
        self.assertEqual(self.mem.facts(), [])

    def test_reflection_saves_facts_retires_outdated_and_logs_episode(self):
        old, _ = self.mem.remember("Lives in Delhi", "profile", 4)
        verdict = {"summary": "User moved to Bengaluru; planning a 10k.",
                   "new_facts": [{"content": "Lives in Bengaluru", "category": "profile", "importance": 4}],
                   "outdated_fact_ids": [old]}
        fake = FakeClaude(reply(text("Congrats on the move!")), reply(text(json.dumps(verdict))))
        m = self.muse(fake)
        m.respond("I just moved to Bengaluru")
        out = m.reflect()
        self.assertEqual(out["forgotten"], [old])
        self.assertEqual([f["content"] for f in self.mem.facts()], ["Lives in Bengaluru"])
        self.assertEqual(self.mem.episodes(1)[0]["summary"], verdict["summary"])
        sent = fake.requests[1]["messages"][0]["content"]
        self.assertIn("I just moved to Bengaluru", sent)
        self.assertNotIn("<muse_context>", sent)

    def test_incognito_skips_reflection(self):
        m = self.muse(FakeClaude(reply(text("hi"))))
        m.incognito = True
        m.respond("hi")
        self.assertIsNone(m.reflect())


if __name__ == "__main__":
    unittest.main()
