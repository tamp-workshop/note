"""
tamp_core.corpus
~~~~~~~~~~~~~~~~
The single source of truth for reading and writing ~/Notes/.
Every filesystem operation goes through Corpus — nothing else touches files directly.

Directory layout:
  ~/Notes/
    daily/      YYYY-MM-DD.md          one file per day, timestamped entries
    notes/      <name>.md              thematic notes
    journal/    YYYY-MM-DD.md          prose journal entries (separate from daily log)
    archive/    anything moved here
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from .config import Config
from .models import DailyLog, Entry, JournalEntry, Note


class Corpus:

    def __init__(self, config: Config) -> None:
        self.config = config
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
        """Append a timestamped entry to a daily log. Returns the new Entry."""
        d    = d or date.today()
        path = self.daily_path(d)
        now  = datetime.now().strftime("%H:%M")
        line = f"- {now} {text}"

        # Ensure the file exists first
        self.load_daily(d)

        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        entry = Entry.parse(line, d)
        assert entry is not None, f"Failed to parse entry we just wrote: {line!r}"
        return entry

    def all_logs(self, limit: int | None = None) -> list[DailyLog]:
        """All daily logs, newest first."""
        paths = sorted(self.config.daily_dir.glob("????-??-??.md"), reverse=True)
        if limit is not None:
            paths = paths[:limit]
        return [DailyLog.from_path(p) for p in paths]

    def all_entries(self, limit_logs: int | None = None) -> list[Entry]:
        """All entries across all logs, newest first."""
        entries = []
        for log in self.all_logs(limit=limit_logs):
            entries.extend(log.entries)
        return entries

    def open_todos(self) -> list[Entry]:
        """All undone entries tagged +todo, across all logs."""
        return [e for e in self.all_entries() if not e.done and "todo" in e.actions]

    def open_signals(self) -> list[Entry]:
        """All undone entries with any action tag."""
        return [e for e in self.all_entries() if not e.done and e.actions]

    def search(self, query: str) -> list[Entry]:
        """Case-insensitive full-text search across all entries."""
        q = query.lower()
        return [e for e in self.all_entries() if q in e.text.lower()]

    def recent_entries(self, n: int = 10) -> list[Entry]:
        return self.all_entries()[:n]

    def mark_done(self, entry: Entry) -> None:
        """Mark an entry done and write the change back to disk."""
        log = self.load_daily(entry.date)
        for e in log.entries:
            if e.time == entry.time and e.text == entry.text:
                e.done = True
                break
        log.write()

    def tag_counts(self) -> dict[str, int]:
        """Count of each @context and +action tag across all entries."""
        from collections import Counter
        counter: Counter = Counter()
        for entry in self.all_entries():
            for tag in entry.contexts:
                counter[f"@{tag}"] += 1
            for tag in entry.actions:
                counter[f"+{tag}"] += 1
        return dict(counter.most_common())

    def entries_by_tag(self, tag: str) -> list[Entry]:
        tag = tag.lstrip("@+")
        return [
            e for e in self.all_entries()
            if tag in e.contexts or tag in e.actions
        ]

    # ── Thematic notes ────────────────────────────────────────────────────────

    def list_notes(self) -> list[Note]:
        paths = sorted(self.config.notes_subdir.glob("*.md"))
        return [Note(name=p.stem, path=p) for p in paths]

    def get_note(self, name: str) -> Note:
        path = self.config.notes_subdir / f"{name}.md"
        return Note(name=name, path=path)

    def create_note(self, name: str) -> Note:
        """Create a note if it doesn't exist, return it either way."""
        note = self.get_note(name)
        if not note.path.exists():
            note.path.write_text(f"# {note.title}\n\n", encoding="utf-8")
        return note

    def rename_note(self, old: str, new: str) -> Note:
        old_note = self.get_note(old)
        if not old_note.path.exists():
            raise FileNotFoundError(f"Note not found: {old}")
        new_note = self.get_note(new)
        old_note.path.rename(new_note.path)
        return new_note

    def delete_note(self, name: str) -> None:
        note = self.get_note(name)
        if note.path.exists():
            note.path.unlink()

    # ── Journal ───────────────────────────────────────────────────────────────
    #
    # Journal entries live in ~/Notes/journal/YYYY-MM-DD.md
    # They are separate from daily logs — prose, not timestamped entries.

    def journal_path(self, d: date | None = None) -> Path:
        d = d or date.today()
        return self.config.journal_dir / f"{d.isoformat()}.md"

    def get_journal(self, d: date | None = None) -> JournalEntry:
        d    = d or date.today()
        path = self.journal_path(d)
        return JournalEntry(date=d, path=path)

    def ensure_journal_file(self, d: date | None = None) -> Path:
        """Create the journal file with a header if it doesn't exist. Return its path."""
        d    = d or date.today()
        path = self.journal_path(d)
        if not path.exists():
            todos = self.load_daily(d).todos
            lines = [f"# {d.strftime('%B %-d, %Y')}\n", ""]
            if todos:
                lines.append("<!-- open todos today -->")
                for t in todos:
                    lines.append(f"<!-- {t.clean_text} -->")
                lines.append("")
            path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def rename_journal(self, old_date: date, new_name: str) -> Path:
        """
        Rename a journal file. new_name should be a date string (YYYY-MM-DD)
        or a freeform name. The .md extension is added if missing.
        """
        old_path = self.journal_path(old_date)
        if not old_path.exists():
            raise FileNotFoundError(f"Journal not found: {old_path.name}")
        if not new_name.endswith(".md"):
            new_name = new_name + ".md"
        new_path = self.config.journal_dir / new_name
        old_path.rename(new_path)
        return new_path

    # ── Folder overview ───────────────────────────────────────────────────────

    def ls(self) -> dict:
        """Return a summary of the Notes directory structure."""
        daily_files   = sorted(self.config.daily_dir.glob("????-??-??.md"), reverse=True)
        note_files    = sorted(self.config.notes_subdir.glob("*.md"))
        journal_files = sorted(self.config.journal_dir.glob("*.md"), reverse=True)
        return {
            "root":    str(self.config.notes_dir),
            "daily":   [f.stem for f in daily_files],
            "notes":   [f.stem for f in note_files],
            "journal": [f.stem for f in journal_files],
        }

    # ── Migration ─────────────────────────────────────────────────────────────

    def migrate_flat(self, source_dir: Path) -> list[Path]:
        """Migrate flat ~/Notes/*.md files (old schema) into daily/ and notes/."""
        import re
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
        migrated = []
        for path in source_dir.glob("*.md"):
            if date_pattern.match(path.name):
                dest = self.config.daily_dir / path.name
            else:
                dest = self.config.notes_subdir / path.name
            if not dest.exists():
                path.rename(dest)
                migrated.append(dest)
        return migrated
