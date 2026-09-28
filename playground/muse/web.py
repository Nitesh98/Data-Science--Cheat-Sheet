"""
Muse as a visual app in your browser, served from your own computer.

    python3 web.py            # real Muse (needs ANTHROPIC_API_KEY), opens http://127.0.0.1:8765
    python3 web.py --demo     # no API key: scripted replies, throwaway memory, same app

Standard library only. The server listens on 127.0.0.1, so only this computer can reach it,
and every state-changing request must carry an `X-Muse` header, which a web page on another
site can't send. No fonts, scripts or analytics are loaded from the internet.

API (all JSON; the chat reply streams back as server-sent events):
  GET  /api/state                       memory, tasks, notes, briefing, session flags
  POST /api/chat      {message}         stream: text / tool / approval / done / error events
  POST /api/approve   {id, ok}          answer a pending approval card
  POST /api/incognito {on}
  POST /api/forget    {id}              POST /api/task {title, due?}   POST /api/task/done {id}
  POST /api/end                         reflect on this conversation, then start a fresh one
  GET  /api/export                      download everything as JSON
  POST /api/wipe                        erase everything
"""
import argparse
import json
import tempfile
import threading
import uuid
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import brain
import config
from memory import Memory

STATIC = Path(__file__).parent / "static"
APPROVAL_TIMEOUT = 300          # seconds before an unanswered approval counts as "no"


class App:
    """One person, one running conversation, shared by all request threads."""

    def __init__(self, mem, call=None, demo=False):
        self.mem, self.call, self.demo = mem, call, demo
        self.busy = threading.Lock()                 # one reply at a time
        self.pending = {}                            # approval id -> [Event, answer]
        self.new_session()

    def new_session(self, incognito=False):
        kw = {"call": self.call} if self.call else {}
        self.muse = brain.Muse(self.mem, incognito=incognito, **kw)

    def state(self):
        m = self.mem
        today = datetime.now().astimezone().date().isoformat()
        overdue, due_today = m.due_tasks(today)
        return {
            "model": config.MODEL, "demo": self.demo, "incognito": self.muse.incognito,
            "db_path": "(temporary demo memory)" if self.demo else str(config.DB_PATH).replace(str(Path.home()), "~"),
            "turns": self.muse.user_turns, "today": today,
            "overdue": overdue, "due_today": due_today,
            "tasks": m.tasks("open"), "done": m.tasks("done")[-20:],
            "facts": m.facts(), "notes": m.notes(), "episodes": m.episodes(5),
        }

    def approve(self, send, name, args):
        aid = uuid.uuid4().hex
        what = json.dumps(args)
        if name == "forget":
            fact = self.mem.fact(args.get("fact_id"))
            what = f"“{fact['content']}”" if fact else f"memory #{args.get('fact_id')}"
        waiter = [threading.Event(), False]
        self.pending[aid] = waiter
        send("approval", {"id": aid, "name": name, "what": what, "reason": args.get("reason", "")})
        waiter[0].wait(APPROVAL_TIMEOUT)
        self.pending.pop(aid, None)
        send("approval_result", {"id": aid, "ok": waiter[1]})
        return waiter[1]


class Handler(BaseHTTPRequestHandler):
    app = None                                       # set in main()
    server_version = "Muse"

    def log_message(self, fmt, *args):               # keep the terminal quiet
        pass

    # ------------------------------------------------------------ helpers
    def _json(self, obj, status=200, headers=None):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def _trusted(self):
        """Only this computer, and only our own page (a foreign site can't set X-Muse)."""
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost") and (self.command == "GET" or self.headers.get("X-Muse") == "1")

    # ------------------------------------------------------------- routes
    def do_GET(self):
        if not self._trusted():
            return self._json({"error": "forbidden"}, 403)
        a = self.app
        if self.path == "/api/state":
            return self._json(a.state())
        if self.path == "/api/export":
            return self._json(a.mem.export(), headers={"Content-Disposition": 'attachment; filename="muse-export.json"'})
        path = "index.html" if self.path in ("/", "/index.html") else self.path.lstrip("/")
        f = (STATIC / path).resolve()
        if not f.is_relative_to(STATIC.resolve()) or not f.is_file():
            return self._json({"error": "not found"}, 404)
        kind = {".html": "text/html; charset=utf-8", ".svg": "image/svg+xml"}.get(f.suffix, "application/octet-stream")
        data = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                                                    "script-src 'self' 'unsafe-inline'; img-src 'self' data:")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if not self._trusted():
            return self._json({"error": "forbidden"}, 403)
        a, body = self.app, self._body()
        route = self.path
        if route == "/api/chat":
            return self._chat(str(body.get("message", "")).strip())
        if route == "/api/approve":
            waiter = a.pending.get(body.get("id"))
            if not waiter:
                return self._json({"error": "no such approval"}, 404)
            waiter[1] = bool(body.get("ok"))
            waiter[0].set()
            return self._json({"ok": True})
        if a.busy.locked() and route in ("/api/end", "/api/wipe", "/api/incognito"):
            return self._json({"error": "Muse is still replying"}, 409)
        if route == "/api/incognito":
            a.muse.incognito = bool(body.get("on"))
        elif route == "/api/forget":
            a.mem.forget(int(body["id"]))
        elif route == "/api/task":
            title = str(body.get("title", "")).strip()
            if title:
                a.mem.add_task(title, body.get("due") or None)
        elif route == "/api/task/done":
            a.mem.complete_task(int(body["id"]))
        elif route == "/api/end":
            with a.busy:
                out = a.muse.reflect()
                a.new_session(incognito=a.muse.incognito)
            return self._json({"reflection": out, "state": a.state()})
        elif route == "/api/wipe":
            a.mem.wipe()
            a.new_session()
        else:
            return self._json({"error": "not found"}, 404)
        return self._json(a.state())

    def _chat(self, message):
        a = self.app
        if not message:
            return self._json({"error": "empty message"}, 400)
        if not a.busy.acquire(blocking=False):
            return self._json({"error": "Muse is still replying"}, 409)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            alive = [True]

            def send(event, data):
                if not alive[0]:
                    return
                try:
                    self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode())
                    self.wfile.flush()
                except OSError:                      # browser tab closed; let the turn finish quietly
                    alive[0] = False

            try:
                a.muse.respond(message,
                               on_text=lambda t: send("text", {"t": t}),
                               on_tool=lambda name, args: send("tool", {"name": name, "args": args}),
                               approve=lambda name, args: a.approve(send, name, args))
                send("done", {})
            except Exception as e:
                send("error", {"message": f"{type(e).__name__}: {e}"})
        finally:
            a.busy.release()


def main():
    ap = argparse.ArgumentParser(description="Muse in your browser.")
    ap.add_argument("--demo", action="store_true", help="no API key: scripted replies, throwaway memory")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    opts = ap.parse_args()

    if opts.demo:
        import demo
        mem = Memory(Path(tempfile.mkdtemp(prefix="muse-demo-")) / "demo.db")
        app = App(mem, call=demo.DemoClaude(mem), demo=True)
    else:
        app = App(Memory(config.DB_PATH))
    Handler.app = app

    url = f"http://127.0.0.1:{opts.port}"
    server = ThreadingHTTPServer(("127.0.0.1", opts.port), Handler)
    print(f"✦ Muse is running at {url}" + ("  (demo mode: scripted replies)" if opts.demo else "")
          + "\n  Ctrl+C to stop. Muse reflects on the conversation before it exits.")
    if not opts.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if app.muse.user_turns and not app.muse.incognito and not opts.demo:
            print("Reflecting on the conversation…")
            try:
                app.muse.reflect()
            except Exception as e:
                print(f"  Couldn't reflect ({type(e).__name__}: {e}).")


if __name__ == "__main__":
    main()
