"""
Muse's long-term memory: one local SQLite file with four tables.

  facts     durable things about you ("prefers morning workouts", "sister is Priya")
  tasks     to-dos and reminders, optionally with a due date and a parent goal
  notes     longer free-form writing (research results, journal entries, plans)
  episodes  one summary per past conversation, so Muse has continuity

Retrieval is BM25 keyword ranking (hand-rolled, stdlib only) blended with each
fact's importance and how recently it was used, so the right few memories are
pulled into each turn instead of dumping everything into the prompt.

Deletes from the agent are SOFT (active = 0) so nothing Muse does on its own is
irreversible; `wipe()` is the user's hard delete.
"""
import json
import math
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = ["profile", "preference", "relationship", "goal", "health", "work", "event", "other"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY, content TEXT NOT NULL, category TEXT NOT NULL,
    importance INTEGER NOT NULL DEFAULT 3, source TEXT NOT NULL DEFAULT 'chat',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_used_at TEXT,
    use_count INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, notes TEXT DEFAULT '', due TEXT,
    priority TEXT NOT NULL DEFAULT 'normal', goal TEXT, status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL, done_at TEXT);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, tags TEXT DEFAULT '',
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT NOT NULL, summary TEXT NOT NULL);
"""

_STOP = set("a an the and or but of to in on at for with is are was were be been am i me my you your "
            "it its this that these those do does did have has had not no so as by from about what "
            "when where who how which will would can could should".split())


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tokenize(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 1]


def bm25(query, docs, k1=1.5, b=0.75):
    """Score each doc (a string) against the query. Returns a list of floats."""
    q = tokenize(query)
    toks = [tokenize(d) for d in docs]
    if not q or not docs:
        return [0.0] * len(docs)
    avg = sum(len(t) for t in toks) / len(toks) or 1
    df = Counter(w for t in toks for w in set(t))
    n = len(docs)
    scores = []
    for t in toks:
        tf = Counter(t)
        s = 0.0
        for w in q:
            if w in tf:
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(t) / avg))
        scores.append(s)
    return scores


def _similar(a, b):
    """Jaccard overlap of content words -- catches near-duplicate facts."""
    ta, tb = set(tokenize(a)), set(tokenize(b))
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


class Memory:
    def __init__(self, path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(_SCHEMA)

    def _rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    # ---------------------------------------------------------------- facts
    def remember(self, content, category="other", importance=3, source="chat"):
        """Store a fact, or refresh a near-duplicate. Returns (id, 'created'|'updated')."""
        category = category if category in CATEGORIES else "other"
        importance = max(1, min(5, int(importance)))
        for f in self.facts():
            if f["category"] == category and _similar(f["content"], content) >= 0.6:
                self.db.execute("UPDATE facts SET content=?, importance=MAX(importance, ?), updated_at=? "
                                "WHERE id=?", (content, importance, now(), f["id"]))
                self.db.commit()
                return f["id"], "updated"
        cur = self.db.execute(
            "INSERT INTO facts (content, category, importance, source, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?)", (content, category, importance, source, now(), now()))
        self.db.commit()
        return cur.lastrowid, "created"

    def facts(self, include_inactive=False):
        where = "" if include_inactive else "WHERE active = 1"
        return self._rows(f"SELECT * FROM facts {where} ORDER BY importance DESC, updated_at DESC")

    def fact(self, fact_id):
        rows = self._rows("SELECT * FROM facts WHERE id = ?", (fact_id,))
        return rows[0] if rows else None

    def forget(self, fact_id):
        cur = self.db.execute("UPDATE facts SET active = 0, updated_at = ? WHERE id = ? AND active = 1",
                              (now(), fact_id))
        self.db.commit()
        return cur.rowcount > 0

    def recall(self, query, limit=8, touch=True):
        """Most relevant active facts: BM25 relevance, nudged by importance and recency of use."""
        facts = self.facts()
        rel = bm25(query, [f"{f['category']} {f['content']}" for f in facts])
        ranked = []
        for f, r in zip(facts, rel):
            if r <= 0:
                continue
            ranked.append((r * (1 + 0.15 * f["importance"]) * (1 + 0.02 * min(f["use_count"], 10)), f))
        ranked.sort(key=lambda x: -x[0])
        hits = [f for _, f in ranked[:limit]]
        if touch and hits:
            self.db.executemany("UPDATE facts SET use_count = use_count + 1, last_used_at = ? WHERE id = ?",
                                [(now(), f["id"]) for f in hits])
            self.db.commit()
        return hits

    # ---------------------------------------------------------------- tasks
    def add_task(self, title, due=None, priority="normal", notes="", goal=None):
        cur = self.db.execute("INSERT INTO tasks (title, due, priority, notes, goal, created_at) "
                              "VALUES (?,?,?,?,?,?)", (title, due, priority, notes, goal, now()))
        self.db.commit()
        return cur.lastrowid

    def tasks(self, status="open", goal=None):
        sql, args = "SELECT * FROM tasks WHERE 1=1", []
        if status != "all":
            sql += " AND status = ?"
            args.append(status)
        if goal:
            sql += " AND goal = ?"
            args.append(goal)
        # open tasks with a due date first (soonest first), then undated by priority
        sql += (" ORDER BY due IS NULL, due, CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, id")
        return self._rows(sql, args)

    def complete_task(self, task_id):
        cur = self.db.execute("UPDATE tasks SET status='done', done_at=? WHERE id=? AND status='open'",
                              (now(), task_id))
        self.db.commit()
        return cur.rowcount > 0

    def due_tasks(self, today):
        """(overdue, due_today) open tasks, comparing ISO date prefixes to `today` (YYYY-MM-DD)."""
        dated = [t for t in self.tasks() if t["due"]]
        return ([t for t in dated if t["due"][:10] < today], [t for t in dated if t["due"][:10] == today])

    # ---------------------------------------------------------------- notes
    def save_note(self, title, body, tags=""):
        cur = self.db.execute("INSERT INTO notes (title, body, tags, created_at) VALUES (?,?,?,?)",
                              (title, body, tags, now()))
        self.db.commit()
        return cur.lastrowid

    def notes(self):
        return self._rows("SELECT * FROM notes ORDER BY id DESC")

    def search_notes(self, query, limit=3):
        notes = self.notes()
        scores = bm25(query, [f"{n['title']} {n['tags']} {n['body']}" for n in notes])
        return [n for s, n in sorted(zip(scores, notes), key=lambda x: -x[0]) if s > 0][:limit]

    # ------------------------------------------------------------- episodes
    def add_episode(self, started_at, summary):
        self.db.execute("INSERT INTO episodes (started_at, ended_at, summary) VALUES (?,?,?)",
                        (started_at, now(), summary))
        self.db.commit()

    def episodes(self, limit=3):
        return self._rows("SELECT * FROM episodes ORDER BY id DESC LIMIT ?", (limit,))

    # ------------------------------------------------------- user controls
    def export(self):
        return {t: self._rows(f"SELECT * FROM {t}") for t in ("facts", "tasks", "notes", "episodes")}

    def export_json(self, path):
        Path(path).write_text(json.dumps(self.export(), indent=2))

    def wipe(self):
        for t in ("facts", "tasks", "notes", "episodes"):
            self.db.execute(f"DELETE FROM {t}")
        self.db.commit()
