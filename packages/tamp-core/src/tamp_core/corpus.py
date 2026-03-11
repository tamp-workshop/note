"""
tamp_core.corpus
~~~~~~~~~~~~~~~~
The single source of truth for reading and writing ~/Notes/.
Every operation goes through Corpus — no other code touches the filesystem directly.
"""

from __future__ import annotations

import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import Config
from .models import DailyLog, Entry, JournalEntry, Note


class Corpus:
    """
    Reads and writes ~/Notes/ according to the tamp schema.

    Usage:
        corpus = Corpus(Config.load())
        today  = corpus.today()
        todos  = corpus.open_todos()
    """

    def __init__(self, config: Config) -> None:
        self.config     = config
        self._undo_stack: list[dict] = []   # session-scoped, in-memory only
        config.ensure_dirs()

    # ── Daily logs ────────────────────────────────────────────────────────────

    def daily_path(self, d: date | None = None) -> Path:
        d = d or date.today()
        return self.config.daily_dir / f"{d.isoformat()}.md"

    def today(self) -> DailyLog:
        return self.load_daily(date.today())

    def load_daily(self, d: date) -> DailyLog:
        path = self.daily_path(d)
        if not path.exists():
            path.write_text(self._daily_header(d) + "\n", encoding="utf-8")
        return DailyLog.from_path(path)

    def _daily_header(self, d: date) -> str:
        return f"# {d.strftime('%A, %B %-d %Y')}\n"

    def append_entry(self, text: str, d: date | None = None) -> Entry:
        """Append a new timestamped entry to a daily log."""
        d    = d or date.today()
        log  = self.load_daily(d)
        now  = datetime.now().strftime("%H:%M")
        path = self.daily_path(d)

        line = f"- {now} {text}"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        entry = Entry.parse(line, d)
        assert entry is not None
        return entry

    def all_logs(self, limit: int | None = None) -> list[DailyLog]:
        """Return all daily logs, newest first."""
        paths = sorted(self.config.daily_dir.glob("????-??-??.md"), reverse=True)
        if limit:
            paths = paths[:limit]
        return [DailyLog.from_path(p) for p in paths]

    def logs_since(self, d: date) -> list[DailyLog]:
        """Return logs from d onwards (inclusive), newest first."""
        return [
            log for log in self.all_logs()
            if log.date >= d
        ]

    # ── Entries (cross-log) ────────────────────────────────────────────────

    def all_entries(self, limit_logs: int | None = None) -> list[Entry]:
        entries = []
        for log in self.all_logs(limit=limit_logs):
            entries.extend(log.entries)
        return entries

    def open_todos(self) -> list[Entry]:
        return [e for e in self.all_entries() if not e.done and "todo" in e.actions]

    def open_signals(self) -> list[Entry]:
        return [e for e in self.all_entries() if not e.done and e.actions]

    def entries_by_tag(self, tag: str) -> list[Entry]:
        tag = tag.lstrip("@+")
        return [
            e for e in self.all_entries()
            if tag in e.contexts or tag in e.actions
        ]

    def search(self, query: str) -> list[Entry]:
        q = query.lower()
        return [e for e in self.all_entries() if q in e.text.lower()]

    def mark_done(self, entry: Entry) -> None:
        """Mark an entry as done and write the change back to disk."""
        log = self.load_daily(entry.date)
        for e in log.entries:
            if e.time == entry.time and e.text == entry.text:
                e.done = True
                break
        log.write()
        self._undo_stack.append({
            "op":   "mark_done",
            "time": entry.time,
            "text": entry.text,
            "date": entry.date,
        })

    def recent_entries(self, n: int = 10) -> list[Entry]:
        entries = self.all_entries()
        return entries[:n]

    # ── Thematic notes ────────────────────────────────────────────────────────

    def list_notes(self) -> list[Note]:
        paths = sorted(self.config.notes_subdir.glob("*.md"))
        return [Note(name=p.stem, path=p) for p in paths]

    def get_note(self, name: str) -> Note:
        path = self.config.notes_subdir / f"{name}.md"
        return Note(name=name, path=path)

    def create_note(self, name: str) -> Note:
        note = self.get_note(name)
        if not note.path.exists():
            note.path.write_text(f"# {note.title}\n\n", encoding="utf-8")
        return note

    def rename_note(self, old: str, new: str) -> Note:
        old_note = self.get_note(old)
        new_note = self.get_note(new)
        old_note.path.rename(new_note.path)
        return new_note

    def delete_note(self, name: str) -> None:
        note = self.get_note(name)
        if note.path.exists():
            content = note.path.read_text(encoding="utf-8")
            note.path.unlink()
            self._undo_stack.append({
                "op":      "delete_note",
                "name":    name,
                "path":    note.path,
                "content": content,
            })

    def undo_last(self) -> str | None:
        """Revert the most recent write operation.

        Returns a human-readable description of what was undone,
        or None if the stack is empty.
        """
        if not self._undo_stack:
            return None

        record = self._undo_stack.pop()

        if record["op"] == "mark_done":
            log = self.load_daily(record["date"])
            for e in log.entries:
                if e.time == record["time"] and e.text == record["text"]:
                    e.done = False
                    break
            log.write()
            return f"{record['time']} {record['text']} — marked undone"

        if record["op"] == "delete_note":
            record["path"].write_text(record["content"], encoding="utf-8")
            return f"{record['name']}.md restored"

        return None  # unknown op, stack was corrupted — silently discard

    def get_log(self, d: date) -> DailyLog | None:
        """Load a daily log for a given date. Returns None if no file exists."""
        path = self.daily_path(d)
        if not path.exists():
            return None
        return DailyLog.from_path(path)

    # ── Journal ───────────────────────────────────────────────────────────────

    def journal_path(self, d: date | None = None) -> Path:
        d = d or date.today()
        return self.config.daily_dir / f"{d.isoformat()}-journal.md"

    def get_journal(self, d: date | None = None) -> JournalEntry:
        d    = d or date.today()
        path = self.journal_path(d)
        return JournalEntry(date=d, path=path)

    def open_journal_in_editor(self, d: date | None = None) -> None:
        """Open today's journal in $EDITOR with a prompt pre-filled."""
        d       = d or date.today()
        journal = self.get_journal(d)
        if not journal.path.exists():
            todos_today = self.load_daily(d).todos
            prompt_lines = [
                f"# {d.strftime('%B %-d, %Y')}\n",
                "",
            ]
            if todos_today:
                prompt_lines.append("<!-- open today -->");
                for t in todos_today:
                    prompt_lines.append(f"<!-- {t.clean_text} -->")
                prompt_lines.append("")
            journal.path.write_text("\n".join(prompt_lines), encoding="utf-8")

        editor = self.config.resolve_editor()
        subprocess.run([editor, str(journal.path)])

    # ── All-tags overview ─────────────────────────────────────────────────────

    def tag_counts(self) -> dict[str, int]:
        from collections import Counter
        c: Counter = Counter()
        for entry in self.all_entries():
            for t in entry.contexts:
                c[f"@{t}"] += 1
            for t in entry.actions:
                c[f"+{t}"] += 1
        return dict(c.most_common())

    # ── Migration ─────────────────────────────────────────────────────────────

    def migrate_flat(self, source_dir: Path) -> list[Path]:
        """
        Migrate flat ~/Notes/*.md files (old schema) to daily/ + notes/.
        Returns list of migrated paths.
        """
        migrated = []
        date_pattern = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}\.md$")

        for path in source_dir.glob("*.md"):
            if date_pattern.match(path.name):
                dest = self.config.daily_dir / path.name
                if not dest.exists():
                    path.rename(dest)
                    migrated.append(dest)
            else:
                dest = self.config.notes_subdir / path.name
                if not dest.exists():
                    path.rename(dest)
                    migrated.append(dest)

        return migrated
