"""
tamp_note.commands
~~~~~~~~~~~~~~~~~~
Slash command registry.

Adding a command:
  1. Define a handler: (Corpus, list[str]) -> CommandResult
  2. Add to REGISTRY at the bottom.

has_args=True  → palette inserts into input, user types args, one Enter to run.
has_args=False → palette executes immediately, no args needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TypeAlias

from tamp_core import Corpus


# ── Output colour palette ────────────────────────────────────────────────────
# Mirrors the Vanguard Outpost palette in app.py — change both together.
_C_AMBER = "#E2B07C"
_C_GREY  = "#9890A2"
_C_DIM   = "#746E80"
_C_TEXT  = "#DDDCE6"


# ── Types ─────────────────────────────────────────────────────────────────────

CommandDict: TypeAlias = dict[str, "Command"]


@dataclass
class CommandResult:
    """Returned by every command handler."""
    output: str    = ""
    kind:   str    = "info"      # info | success | error | table | todo_list
    data:   object = None        # structured payload (e.g. list[Entry] for todos)
    action: str    = ""          # "open_editor:<path>" | "exit" | "clear_log" | ""


@dataclass
class Command:
    name:        str
    description: str
    usage:       str
    handler:     Callable[[Corpus, list[str]], CommandResult]
    has_args:    bool = False    # True = needs user-supplied args after command name


# ── Handlers ──────────────────────────────────────────────────────────────────

def _cmd_todo(corpus: Corpus, args: list[str]) -> CommandResult:
    todos = corpus.open_todos()
    if not todos:
        return CommandResult(output="no open todos. clean slate.", kind="success")
    return CommandResult(
        kind = "todo_list",
        data = sorted(todos, key=lambda e: e.age_days, reverse=True),
    )


def _cmd_find(corpus: Corpus, args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(output="usage: /find <query>", kind="error")

    # Multi-word = AND: every word must appear in the entry text
    words   = [a.lower() for a in args]
    entries = corpus.all_entries()
    results = [
        e for e in entries
        if all(w in e.text.lower() for w in words)
    ]

    if not results:
        query = " ".join(args)
        return CommandResult(output=f"nothing found for '{query}'", kind="info")

    total = len(results)
    shown = results[:20]

    # Group by date, same style as /last
    lines: list[str] = []
    if total > 20:
        lines.append(f"  [{_C_DIM}]showing 20 of {total} matches[/{_C_DIM}]")
    current_date = None
    for e in shown:
        if e.date != current_date:
            lines.append(f"\n  [{_C_AMBER}]{e.date.strftime('%A, %B %-d')}[/{_C_AMBER}]")
            current_date = e.date
        if e.done:
            lines.append(f"  [{_C_DIM}]{e.time}  ~~{e.text}~~[/{_C_DIM}]")
        else:
            lines.append(f"  {e.time}  {e.text}")

    return CommandResult(output="\n".join(lines), kind="table", data=shown)


def _cmd_notes(corpus: Corpus, args: list[str]) -> CommandResult:
    notes = corpus.list_notes()
    if not notes:
        return CommandResult(output="no thematic notes yet. try /open <name>", kind="info")
    lines = [f"  {n.name}" for n in notes]
    return CommandResult(output="\n".join(lines), kind="table", data=notes)


def _cmd_open(corpus: Corpus, args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(output="usage: /open <name>", kind="error")
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
    old_name = args[0].removesuffix(".md")
    new_name = args[1].removesuffix(".md")
    try:
        corpus.rename_note(old_name, new_name)
        return CommandResult(output=f"renamed {old_name} → {new_name}", kind="success")
    except FileNotFoundError:
        return CommandResult(output=f"note '{old_name}' not found", kind="error")


def _cmd_delete(corpus: Corpus, args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(output="usage: /delete <name> [--confirm]", kind="error")
    name = args[0].removesuffix(".md")
    note = corpus.get_note(name)
    if not note.path.exists():
        return CommandResult(output=f"note '{name}' not found", kind="error")
    if "--confirm" not in args:
        return CommandResult(
            output=f"  delete {name}.md permanently?  run: /delete {name} --confirm",
            kind="info",
        )
    corpus.delete_note(name)
    return CommandResult(output=f"deleted {name}.md", kind="success")


def _cmd_tags(corpus: Corpus, args: list[str]) -> CommandResult:
    counts = corpus.tag_counts()
    if not counts:
        return CommandResult(output="no tags yet.", kind="info")

    # Optional filter: /tags @dev or /tags dev
    if args:
        q = args[0].lstrip("@+").lower()
        prefix = "@" if args[0].startswith("@") else "+" if args[0].startswith("+") else None
        counts = {
            k: v for k, v in counts.items()
            if q in k.lstrip("@+").lower()
            and (prefix is None or k.startswith(prefix))
        }
        if not counts:
            return CommandResult(output=f"no tags matching {args[0]!r}", kind="info")

        entries = corpus.entries_by_tag(args[0])
        lines   = [f"  [{_C_AMBER}]{args[0]}[/{_C_AMBER}]  [{_C_DIM}]{len(entries)} entries[/{_C_DIM}]", ""]
        for e in entries[:15]:
            mark = f"[{_C_DIM}]~~[/{_C_DIM}]" if e.done else "  "
            lines.append(f"  {mark} {e.date.isoformat()}  {e.time}  {e.text}")
        if len(entries) > 15:
            lines.append(f"  [{_C_DIM}]… {len(entries) - 15} more[/{_C_DIM}]")
        return CommandResult(output="\n".join(lines), kind="table")

    lines = [f"  {tag:<20} {count}" for tag, count in list(counts.items())[:20]]
    return CommandResult(output="\n".join(lines), kind="table")


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
        mark = f"[{_C_DIM}]~~[/{_C_DIM}]" if e.done else "  "
        lines.append(f"  {mark}{e.time}  {e.text}")
    return CommandResult(output="\n".join(lines), kind="table", data=entries)


def _cmd_stats(corpus: Corpus, args: list[str]) -> CommandResult:
    from tamp_core.stats import analyse
    s = analyse(corpus)

    if not s.has_enough_data:
        return CommandResult(
            output=(
                f"  {s.total_logs} logs · {s.total_entries} entries\n\n"
                f"  pattern analysis activates after {14 - s.total_logs} more days.\n"
                f"  until then: plain counts, no inference."
            ),
            kind="info",
        )

    lines = [
        "",
        f"  corpus          {s.total_logs} logs · {s.total_entries} entries",
        f"  active days     {s.active_days}  ({s.active_days/s.total_logs:.0%})",
        f"  avg / day       {s.avg_entries_day:.1f} entries",
        (f"  peak hour       {s.peak_hour:02d}:00"
         if s.peak_hour is not None else "  peak hour       —"),
        "",
        f"  open todos      {s.open_todos}",
        f"  oldest open     {s.oldest_open_days}d",
        f"  completion      {s.completion_rate:.0%}",
        "",
    ]
    if s.top_contexts:
        lines.append("  top @contexts   " +
                     "  ".join(f"{t} ({c})" for t, c in s.top_contexts))
    if s.top_actions:
        lines.append("  top +actions    " +
                     "  ".join(f"{t} ({c})" for t, c in s.top_actions))
    if s.insights:
        lines += ["", "  patterns"]
        lines += [f"  · {i.text}" for i in s.insights]
    lines += ["", "  all data is local. nothing leaves this machine.", ""]
    return CommandResult(output="\n".join(lines), kind="table")


def _cmd_status(corpus: Corpus, args: list[str]) -> CommandResult:
    """Quick one-glance snapshot: today, todos, total entries, streak.

    Avoids the full analyse() engine — direct counts only.
    """
    from datetime import date, timedelta
    today   = corpus.today()
    todos   = corpus.open_todos()
    entries = corpus.all_entries()

    logs    = corpus.all_logs()
    log_map = {log.date: log for log in logs}
    streak  = 0
    cursor  = date.today()
    while cursor in log_map and log_map[cursor].entries:
        streak += 1
        cursor -= timedelta(days=1)

    weekday    = date.today().strftime("%A")
    todo_label = f"{len(todos)} todo" if len(todos) == 1 else f"{len(todos)} todos"
    parts = [
        weekday,
        f"{len(today.entries)} entries today",
        f"{len(entries)} total",
        todo_label,
    ]
    if streak >= 2:
        parts.append(f"{streak}d streak")
    return CommandResult(output="  " + "  ·  ".join(parts), kind="info")


def _cmd_journal(corpus: Corpus, args: list[str]) -> CommandResult:
    """Open today's journal, pre-filling with open todos as prompts."""
    from datetime import date
    d    = date.today()
    path = corpus.journal_path(d)

    # Pre-fill only if the file doesn't exist yet
    if not path.exists():
        todos = corpus.load_daily(d).todos
        lines = [f"# {d.strftime('%B %-d, %Y')}", ""]
        if todos:
            lines.append("<!-- open todos -->")
            for t in todos:
                lines.append(f"<!-- {t.clean_text} -->")
            lines.append("")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return CommandResult(
        output = "opening journal",
        kind   = "success",
        action = f"open_editor:{path}",
    )


def _cmd_config(corpus: Corpus, args: list[str]) -> CommandResult:
    from tamp_core.config import CONFIG_FILE
    # Ensure the config file exists — opening a blank file would lose defaults
    if not CONFIG_FILE.exists():
        corpus.config.save()
    return CommandResult(
        output = "opening config",
        kind   = "success",
        action = f"open_editor:{str(CONFIG_FILE)}",
    )


def _cmd_ls(corpus: Corpus, args: list[str]) -> CommandResult:
    cfg         = corpus.config
    daily_files = sorted(cfg.daily_dir.glob("????-??-??.md"), reverse=True)
    notes       = corpus.list_notes()

    lines = [f"\n  [{_C_AMBER}]{cfg.notes_dir}[/{_C_AMBER}]"]
    lines.append(f"  [{_C_DIM}]daily/[/{_C_DIM}]  ({len(daily_files)} logs)")
    for f in daily_files[:5]:
        lines.append(f"    [{_C_GREY}]{f.stem}[/{_C_GREY}]")
    if len(daily_files) > 5:
        lines.append(f"    [{_C_DIM}]… {len(daily_files) - 5} more[/{_C_DIM}]")

    lines.append(f"  [{_C_DIM}]notes/[/{_C_DIM}]  ({len(notes)} notes)")
    for n in notes:
        lines.append(f"    [{_C_TEXT}]{n.name}.md[/{_C_TEXT}]")
    if not notes:
        lines.append(f"    [{_C_DIM}]empty — try /open <n>[/{_C_DIM}]")
    lines.append("")
    return CommandResult(output="\n".join(lines), kind="table")


def _cmd_export(corpus: Corpus, args: list[str]) -> CommandResult:
    """Export entries to a file or print to log.

    /export                        → today's entries to log
    /export 2026-03-06             → specific date to log
    /export 2026-03-01 2026-03-06  → date range to log
    /export out.md                 → today to file
    /export 2026-03-06 out.md      → specific date to file
    /export 2026-03-01 2026-03-06 out.md  → range to file
    """
    from datetime import date as date_type
    from pathlib import Path
    import re as _re

    date_pat = _re.compile(r'^\d{4}-\d{2}-\d{2}$')
    dates: list[date_type] = []
    output_path: str | None = None

    for arg in args:
        if date_pat.match(arg):
            try:
                dates.append(date_type.fromisoformat(arg))
            except ValueError:
                return CommandResult(output=f"invalid date: {arg}", kind="error")
        elif arg == "today":
            dates.append(date_type.today())
        else:
            output_path = arg  # last non-date arg = output path

    # Resolve date range
    if len(dates) == 0:
        start_date = end_date = date_type.today()
    elif len(dates) == 1:
        start_date = end_date = dates[0]
    else:
        start_date, end_date = min(dates), max(dates)

    # Collect all logs in range
    from datetime import timedelta
    cursor   = start_date
    all_logs = []
    while cursor <= end_date:
        log = corpus.get_log(cursor)
        if log and log.entries:
            all_logs.append(log)
        cursor += timedelta(days=1)

    if not all_logs:
        label = (start_date.isoformat() if start_date == end_date
                 else f"{start_date.isoformat()} – {end_date.isoformat()}")
        return CommandResult(output=f"no entries for {label}", kind="info")

    # Build markdown content
    content_lines: list[str] = []
    for log in all_logs:
        date_str = log.date.strftime("%A, %-d %B %Y")
        content_lines += [f"# {date_str}", ""]
        for e in log.entries:
            prefix = "~~" if e.done else "-"
            content_lines.append(f"{prefix} {e.time} {e.text}")
        content_lines.append("")
    content = "\n".join(content_lines)

    total_entries = sum(len(l.entries) for l in all_logs)

    if output_path:
        dest = Path(output_path).expanduser().resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return CommandResult(
            output=f"exported {total_entries} entries ({len(all_logs)} days) → {dest}",
            kind="success",
        )

    return CommandResult(output=content, kind="table")


def _cmd_undo(corpus: Corpus, args: list[str]) -> CommandResult:
    """Revert the last write operation (done-mark or delete)."""
    result = corpus.undo_last()
    if result is None:
        return CommandResult(output="nothing to undo.", kind="info")
    return CommandResult(output=f"undone: {result}", kind="success")


def _cmd_clear(corpus: Corpus, args: list[str]) -> CommandResult:
    """Clear the log output. Your notes are untouched — screen only."""
    return CommandResult(action="clear_log")


def _cmd_exit(corpus: Corpus, args: list[str]) -> CommandResult:
    return CommandResult(action="exit")


# ── Registry ──────────────────────────────────────────────────────────────────

REGISTRY: CommandDict = {
    cmd.name: cmd for cmd in [
        Command("todo",    "interactive todo list",         "/todo",                 _cmd_todo),
        Command("find",    "full-text search",              "/find <query>",         _cmd_find,   has_args=True),
        Command("last",    "recent entries",                "/last [n]",             _cmd_last,   has_args=True),
        Command("status",  "quick snapshot",                "/status",               _cmd_status),
        Command("journal", "open today's journal",          "/journal",              _cmd_journal),
        Command("tags",    "tag counts",                    "/tags [@tag]",          _cmd_tags,   has_args=True),
        Command("stats",   "corpus stats + patterns",       "/stats",                _cmd_stats),
        Command("ls",      "notes folder overview",         "/ls",                   _cmd_ls),
        Command("notes",   "list thematic notes",           "/notes",                _cmd_notes),
        Command("open",    "open or create a note",         "/open <n>",             _cmd_open,   has_args=True),
        Command("rename",  "rename a note",                 "/rename <old> <new>",   _cmd_rename, has_args=True),
        Command("delete",  "delete a note",                 "/delete <n>",           _cmd_delete, has_args=True),
        Command("export",  "export entries to file",        "/export [date] [file]", _cmd_export, has_args=True),
        Command("undo",    "revert last write",             "/undo",                 _cmd_undo),
        Command("clear",   "clear log output",              "/clear",                _cmd_clear),
        Command("config",  "open config in $EDITOR",        "/config",               _cmd_config),
        Command("exit",    "quit tamp-note",                "/exit",                 _cmd_exit),
    ]
}


def dispatch(corpus: Corpus, raw: str) -> CommandResult:
    """Parse and execute a slash command string e.g. '/find @dev'."""
    parts   = raw.lstrip("/").split()
    if not parts:
        return CommandResult()
    name    = parts[0].lower()
    args    = parts[1:]
    command = REGISTRY.get(name)
    if not command:
        close = [c for c in REGISTRY if c.startswith(name)]
        hint  = f" — did you mean /{close[0]}?" if len(close) == 1 else ""
        return CommandResult(output=f"unknown: /{name}{hint}", kind="error")
    return command.handler(corpus, args)
