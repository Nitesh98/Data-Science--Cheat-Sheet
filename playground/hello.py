"""
A tiny first script — proof that Claude Code can write and run real code for you.

Try asking Claude things like:
  - "add a function that reverses a string, and a test for it"
  - "explain what this script does, line by line"
  - "make this print the current date too"
"""

def greet(name: str) -> str:
    return f"Hello, {name}! Welcome to Claude Code."


if __name__ == "__main__":
    print(greet("Nitesh"))
    print("This file lives at playground/hello.py — edit it, or ask Claude to.")
