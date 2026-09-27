"""
Chat with Muse in your terminal.

    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 muse.py              # add --incognito for a conversation that leaves no trace

Type /help inside for commands. Your memory lives in ~/.muse/muse.db (set MUSE_HOME to move it).
"""
import argparse
import os
import sys
from datetime import datetime

import brain
import config
from memory import Memory

# ANSI colours, only on a real terminal (and never when NO_COLOR is set)
_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code):
    return (lambda s: f"\033[{code}m{s}\033[0m") if _COLOR else (lambda s: s)


bold, dim, cyan, magenta, yellow, red, green = map(_c, ("1", "2", "1;36", "1;35", "33", "1;31", "32"))

YOU, MUSE = cyan("you ›") + " ", magenta("muse ›") + " "

HELP = f"""{bold("Commands")}
  /brief             what's overdue, due today, and where we left off
  /memory [query]    show what Muse knows about you (or search it)
  /forget <id>       delete a memory             /tasks [all|done]   list tasks
  /done <id>         complete a task             /notes              list saved notes
  /incognito         toggle: nothing from here on is saved
  /export <file>     dump all your data to JSON  /wipe               erase everything (asks first)
  /quit              reflect on the chat, save what matters, exit
{dim("Anything else is a message to Muse.")}"""


def brief(mem):
    today = datetime.now().astimezone().date().isoformat()
    overdue, due = mem.due_tasks(today)
    lines = [f"  {red('!')} overdue  #{t['id']} {t['title']} {dim('(due ' + t['due'] + ')')}" for t in overdue]
    lines += [f"  {yellow('•')} today    #{t['id']} {t['title']}" for t in due]
    open_n = len(mem.tasks())
    if open_n:
        lines.append(dim(f"  {open_n} open task{'s' if open_n != 1 else ''} in total · /tasks to see them"))
    last = mem.episodes(1)
    if last:
        lines.append(f"  {bold('Last time')} {dim(last[0]['ended_at'][:10])}: {last[0]['summary']}")
    return "\n".join(lines) or dim("  Nothing pending. A clean slate.")


def ask(prompt):
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


class Chat:
    """Terminal rendering for one reply: streamed text, tool activity and approval prompts."""

    def __init__(self, mem):
        self.mem = mem
        self.at_line_start = False

    def text(self, t):
        print(t, end="", flush=True)
        self.at_line_start = t.endswith("\n")

    def _newline(self):
        if not self.at_line_start:
            print()
            self.at_line_start = True

    def tool(self, name, args):
        detail = (args.get("query") or args.get("content") or args.get("title") or args.get("goal")
                  or args.get("expression") or "")
        if "task_id" in args:
            detail = f"task #{args['task_id']}"
        if "fact_id" in args:
            detail = f"memory #{args['fact_id']}"
        if name == "create_plan":
            detail += f" ({len(args.get('steps', []))} steps)"
        self._newline()
        print(dim(f"  ⋯ {name}  {str(detail)[:72]}".rstrip()), flush=True)

    def approve(self, name, args):
        self._newline()
        what = args
        if name == "forget":
            fact = self.mem.fact(args.get("fact_id"))
            what = f"“{fact['content']}”" if fact else f"memory #{args.get('fact_id')}"
        print(f"  {yellow('?')} Muse wants to {bold(name)} {what}")
        if args.get("reason"):
            print(dim(f"    reason: {args['reason']}"))
        ok = ask(f"    Allow? {dim('[y/N]')} ")
        print(dim("    approved") if ok else dim("    declined"))
        return ok


def command(line, muse, mem):
    """Handle a /command. Returns False when the user wants to quit."""
    cmd, _, arg = line[1:].partition(" ")
    arg = arg.strip()
    if cmd in ("quit", "exit", "q"):
        return False
    if cmd == "help":
        print(HELP)
    elif cmd == "brief":
        print(brief(mem))
    elif cmd == "memory":
        facts = mem.recall(arg, 20, touch=False) if arg else mem.facts()
        print(bold("  What Muse knows about you") if not arg else bold(f"  Memories matching “{arg}”"))
        for f in facts:
            print(f"  {dim('#' + str(f['id'])):<4} {f['content']}  "
                  + dim(f"{f['category']} · importance {f['importance']} · via {f['source']}"))
        if not facts:
            print(dim("  (nothing yet)"))
    elif cmd == "forget" and arg.isdigit():
        print("  Forgotten." if mem.forget(int(arg)) else "  No such memory.")
    elif cmd == "tasks":
        rows = mem.tasks(arg or "open")
        print(bold(f"  Tasks ({arg or 'open'})"))
        for t in rows:
            box = green("✓") if t["status"] == "done" else "○"
            print(f"  {box} {dim('#' + str(t['id'])):<4} {t['title']:<24}" + (f" {yellow(t['due'])}" if t["due"] else "")
                  + (dim(f"  · {t['goal']}") if t["goal"] else ""))
        if not rows:
            print(dim("  (none)"))
    elif cmd == "done" and arg.isdigit():
        print("  Done." if mem.complete_task(int(arg)) else "  No such open task.")
    elif cmd == "notes":
        for n in mem.notes():
            print(f"  {dim('#' + str(n['id']))} {n['title']}  {dim(n['created_at'][:10])}")
        if not mem.notes():
            print(dim("  (no notes yet)"))
    elif cmd == "incognito":
        muse.incognito = not muse.incognito
        print(f"  Incognito {'ON: nothing from here on is saved' if muse.incognito else 'OFF'}.")
    elif cmd == "export" and arg:
        mem.export_json(arg)
        print(f"  Exported to {arg}.")
    elif cmd == "wipe":
        if ask("  Erase ALL memories, tasks, notes and history? Type y to confirm: "):
            mem.wipe()
            print("  Everything erased.")
    else:
        print(HELP)
    return True


def main():
    ap = argparse.ArgumentParser(description="Muse, your personal AI agent.")
    ap.add_argument("--incognito", action="store_true", help="save nothing from this session")
    opts = ap.parse_args()

    mem = Memory(config.DB_PATH)
    muse = brain.Muse(mem, incognito=opts.incognito)
    print(f"{magenta('✦ Muse')}  {dim(config.MODEL + ' · memory at ' + str(config.DB_PATH))}"
          + (yellow("  [incognito]") if opts.incognito else ""))
    print(brief(mem) + "\n" + dim("  /help for commands") + "\n")

    while True:
        try:
            line = input(YOU).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.startswith("/"):
            if not command(line, muse, mem):
                break
            print()
            continue
        chat = Chat(mem)
        print(MUSE, end="", flush=True)
        try:
            muse.respond(line, on_text=chat.text, on_tool=chat.tool, approve=chat.approve)
        except KeyboardInterrupt:
            print(dim("\n  (interrupted)"))
        except Exception as e:
            print(red(f"\n  [error] {type(e).__name__}: {e}"))
        print("\n")

    if muse.incognito or muse.user_turns == 0:
        return
    print(dim("Reflecting on our conversation…"), flush=True)
    try:
        out = muse.reflect()
    except Exception as e:
        print(f"  Couldn't reflect ({type(e).__name__}: {e}); your explicit memories are still saved.")
        return
    if out:
        n, gone = len(out["saved"]), len(out["forgotten"])
        learned = f"Learned {n} new thing{'s' if n != 1 else ''}" if n else "Nothing new to remember"
        print(f"  {learned}" + (f", retired {gone} outdated" if gone else "") + ". See you next time ✦")


if __name__ == "__main__":
    sys.exit(main())
