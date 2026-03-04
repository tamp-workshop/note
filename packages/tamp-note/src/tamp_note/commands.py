"""
tamp_note.commands
~~~~~~~~~~~~~~~~~~
Every slash command lives here as a plain function.

To add a command:
  1. Write a handler:  def _cmd_foo(corpus, args) -> CommandResult
  2. Register it in REGISTRY at the bottom.

has_args = True  means the palette drops the command into the input field
                 so the user can type arguments before pressing Enter.
has_args = False means the palette executes the command immediately.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, TypeAlias

from tamp_core import Corpus


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class CommandResult:
    output: str    = ""
    kind:   str    = "info"       # info | success | error | table | todo_list
    data:   object = None         # structured payload for the TUI to act on
    action: str    = ""           # "open_editor:<path>" | "exit" | ""


# ── Command descriptor ────────────────────────────────────────────────────────

@dataclass
class Command:
    name:        str
    description: str
    usage:       str
    handler:     Callable[[Corpus, list[str]], CommandResult]
    has_args:    bool = False


# ── Type alias ────────────────────────────────────────────────────────────────

CommandDict: TypeAlias = dict[str, Command]


# ── Handlers ──────────────────────────────────────────────────────────────────

def _cmd_todo(corpus: Corpus, args: list[str]) -> CommandResult:
    todos = corpus.open_todos()
    if not todos:
        return CommandResult(output="no open todos. clean slate.", kind="success")
    sorted_todos = sorted(todos, key=lambda e: e.age_days, reverse=True)
    return CommandResult(kind="todo_list", data=sorted_todos)


def _cmd_find(corpus: Corpus, args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(output="usage: /find <query>", kind="error")
    query   = " ".join(args)
    results = corpus.search(query)
    if not results:
        return CommandResult(output=f"nothing found for '{query}'", kind="info")
    lines = [f"  {e.date.isoformat()}  {e.time}  {e.text}" for e in results[:20]]
    return CommandResult(output="\n".join(lines), kind="table", data=results)


def _cmd_last(corpus: Corpus, args: list[str]) -> CommandResult:
    n       = int(args[0]) if args and args[0].isdigit() else 10
    entries = corpus.recent_entries(n)
    if not entries:
        return CommandResult(output="no entries yet.", kind="info")
    lines: list[str] = []
    current_date = None
    for e in entries:
        if e.date != current_date:
            lines.append(f"\n  {e.date.strftime('%A, %B %-d')}")
            current_date = e.date
        prefix = "[#746E80]~~[/#746E80] " if e.done else "   "
        lines.append(f"  {prefix}{e.time}  {e.text}")
    return CommandResult(output="\n".join(lines), kind="table", data=entries)


def _cmd_notes(corpus: Corpus, args: list[str]) -> CommandResult:
    notes = corpus.list_notes()
    if not notes:
        return CommandResult(output="no thematic notes yet. try /new <name>", kind="info")
    lines = [f"  {n.name}" for n in notes]
    return CommandResult(output="\n".join(lines), kind="table", data=notes)


def _cmd_open(corpus: Corpus, args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(output="usage: /open <name>", kind="error")
    note = corpus.create_note(args[0])
    return CommandResult(
        output = f"opening {args[0]}.md",
        kind   = "success",
        action = f"open_editor:{note.path}",
    )


def _cmd_new(corpus: Corpus, args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(output="usage: /new <name>", kind="error")
    name = args[0].lower().replace(" ", "-")
    note = corpus.create_note(name)
    return CommandResult(
        output = f"opening {name}.md",
        kind   = "success",
        action = f"open_editor:{note.path}",
    )


def _cmd_rename(corpus: Corpus, args: list[str]) -> CommandResult:
    if len(args) < 2:
        return CommandResult(output="usage: /rename <old> <new>", kind="error")
    try:
        corpus.rename_note(args[0], args[1])
        return CommandResult(output=f"renamed {args[0]} → {args[1]}", kind="success")
    except FileNotFoundError:
        return CommandResult(output=f"note '{args[0]}' not found", kind="error")


def _cmd_delete(corpus: Corpus, args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(output="usage: /delete <name>", kind="error")
    note = corpus.get_note(args[0])
    if not note.path.exists():
        return CommandResult(output=f"note '{args[0]}' not found", kind="error")
    corpus.delete_note(args[0])
    return CommandResult(output=f"deleted {args[0]}.md", kind="success")


def _cmd_tags(corpus: Corpus, args: list[str]) -> CommandResult:
    counts = corpus.tag_counts()
    if not counts:
        return CommandResult(output="no tags yet.", kind="info")
    lines = [f"  {tag:<20} {count}" for tag, count in list(counts.items())[:20]]
    return CommandResult(output="\n".join(lines), kind="table")


def _cmd_stats(corpus: Corpus, args: list[str]) -> CommandResult:
    from tamp_core.stats import analyse
    s = analyse(corpus)
    if not s.has_enough_data:
        return CommandResult(
            output=(
                f"  {s.total_logs} logs · {s.total_entries} entries\n\n"
                f"  pattern analysis activates after {14 - s.total_logs} more days."
            ),
            kind="info",
        )
    lines = [
        "",
        f"  corpus        {s.total_logs} logs · {s.total_entries} entries",
        f"  active days   {s.active_days}  ({s.active_days / s.total_logs:.0%})",
        f"  avg / day     {s.avg_entries_day:.1f} entries",
        f"  peak hour     {s.peak_hour:02d}:00" if s.peak_hour is not None else "  peak hour     —",
        "",
        f"  open todos    {s.open_todos}",
        f"  oldest open   {s.oldest_open_days}d",
        f"  completion    {s.completion_rate:.0%}",
        "",
    ]
    if s.top_contexts:
        lines.append("  top @contexts  " + "  ".join(f"{t} ({c})" for t, c in s.top_contexts))
    if s.top_actions:
        lines.append("  top +actions   " + "  ".join(f"{t} ({c})" for t, c in s.top_actions))
    if s.insights:
        lines += ["", "  patterns"]
        lines += [f"  · {i.text}" for i in s.insights]
    lines += ["", "  all data is local. nothing leaves this machine.", ""]
    return CommandResult(output="\n".join(lines), kind="table")


def _cmd_journal(corpus: Corpus, args: list[str]) -> CommandResult:
    """
    /journal         → open today's journal
    /journal rename <new-name>  → rename today's journal file
    """
    if args and args[0] == "rename":
        if len(args) < 2:
            return CommandResult(output="usage: /journal rename <new-name>", kind="error")
        try:
            new_path = corpus.rename_journal(date.today(), args[1])
            return CommandResult(output=f"renamed to {new_path.name}", kind="success")
        except FileNotFoundError as e:
            return CommandResult(output=str(e), kind="error")

    path = corpus.ensure_journal_file()
    return CommandResult(
        output = f"opening journal · {date.today().isoformat()}",
        kind   = "success",
        action = f"open_editor:{path}",
    )


def _cmd_ls(corpus: Corpus, args: list[str]) -> CommandResult:
    overview = corpus.ls()
    lines    = [f"\n  [#E2B07C]{overview['root']}[/#E2B07C]"]

    daily = overview["daily"]
    lines.append(f"  [#746E80]daily/[/#746E80]    {len(daily)} logs")
    for stem in daily[:5]:
        lines.append(f"    [#9890A2]{stem}[/#9890A2]")
    if len(daily) > 5:
        lines.append(f"    [#746E80]… {len(daily) - 5} more[/#746E80]")

    journal = overview["journal"]
    lines.append(f"  [#746E80]journal/[/#746E80]  {len(journal)} entries")
    for stem in journal[:3]:
        lines.append(f"    [#9890A2]{stem}[/#9890A2]")
    if len(journal) > 3:
        lines.append(f"    [#746E80]… {len(journal) - 3} more[/#746E80]")

    notes = overview["notes"]
    lines.append(f"  [#746E80]notes/[/#746E80]    {len(notes)} notes")
    for stem in notes:
        lines.append(f"    [#DDDCE6]{stem}.md[/#DDDCE6]")
    if not notes:
        lines.append("    [#746E80]empty — try /new <name>[/#746E80]")

    lines.append("")
    return CommandResult(output="\n".join(lines), kind="table")


def _cmd_config(corpus: Corpus, args: list[str]) -> CommandResult:
    from tamp_core.config import CONFIG_FILE
    return CommandResult(
        output = f"opening config · {CONFIG_FILE}",
        kind   = "success",
        action = f"open_editor:{CONFIG_FILE}",
    )


def _cmd_exit(corpus: Corpus, args: list[str]) -> CommandResult:
    return CommandResult(action="exit")


def _cmd_help(corpus: Corpus, args: list[str]) -> CommandResult:
    lines = [
        "",
        "  commands",
        "  ──────────────────────────────────────────",
        "  /todo              interactive todo list",
        "  /find <query>      full-text search",
        "  /last [n]          recent entries (default 10)",
        "  /ls                notes folder overview",
        "  /notes             list thematic notes",
        "  /open <name>       open or create a note",
        "  /new <name>        create a new note",
        "  /rename <old> <new>",
        "  /delete <name>",
        "  /tags              tag counts",
        "  /stats             corpus stats + patterns",
        "  /journal           open today's journal",
        "  /journal rename <name>   rename journal file",
        "  /config            open config in $EDITOR",
        "  /exit              quit",
        "",
        "  tags",
        "  ──────────────────────────────────────────",
        "  @word   context tag   e.g. @dev @health",
        "  +word   action tag    e.g. +todo +read +idea",
        "",
        "  example:  dentist appointment @health +todo",
        "  type @ or + while writing to autocomplete known tags",
        "",
        "  shortcuts",
        "  ──────────────────────────────────────────",
        "  /         open command palette",
        "  ?         this help",
        "  ↑ / ↓    command history",
        "  ctrl+r    jump to /find",
        "  ctrl+d    quit",
        "",
    ]
    return CommandResult(output="\n".join(lines), kind="info")


# ── Registry ──────────────────────────────────────────────────────────────────
#
# Order here is the order shown in the command palette.
# Frequency-first: the commands you use most are at the top.

REGISTRY: CommandDict = {
    cmd.name: cmd for cmd in [
        Command("todo",    "interactive todo list",       "/todo",               _cmd_todo),
        Command("find",    "full-text search",            "/find <query>",       _cmd_find,   has_args=True),
        Command("last",    "recent entries",              "/last [n]",           _cmd_last),
        Command("journal", "open today's journal",        "/journal",            _cmd_journal),
        Command("ls",      "notes folder overview",       "/ls",                 _cmd_ls),
        Command("notes",   "list thematic notes",         "/notes",              _cmd_notes),
        Command("tags",    "tag counts",                  "/tags",               _cmd_tags),
        Command("stats",   "corpus stats + patterns",     "/stats",              _cmd_stats),
        Command("open",    "open or create a note",       "/open <name>",        _cmd_open,   has_args=True),
        Command("new",     "create a new note",           "/new <name>",         _cmd_new,    has_args=True),
        Command("rename",  "rename a note",               "/rename <old> <new>", _cmd_rename, has_args=True),
        Command("delete",  "delete a note",               "/delete <name>",      _cmd_delete, has_args=True),
        Command("config",  "open config in $EDITOR",      "/config",             _cmd_config),
        Command("help",    "commands and tag reference",  "/help",               _cmd_help),
        Command("exit",    "quit tamp-note",              "/exit",               _cmd_exit),
    ]
}


def dispatch(corpus: Corpus, raw: str) -> CommandResult:
    """Parse and execute a slash command string, e.g. '/find @dev'."""
    parts = raw.lstrip("/").split()
    if not parts:
        return CommandResult()

    name    = parts[0].lower()
    args    = parts[1:]
    command = REGISTRY.get(name)

    if command is None:
        # Suggest the closest match if there is exactly one
        matches = [c for c in REGISTRY if c.startswith(name)]
        hint    = f" — did you mean /{matches[0]}?" if len(matches) == 1 else ""
        return CommandResult(output=f"unknown command: /{name}{hint}", kind="error")

    return command.handler(corpus, args)
