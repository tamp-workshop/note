"""
tamp_core.models
~~~~~~~~~~~~~~~~
Dataclasses representing the tamp-note schema (see SCHEMA.md).
All tools in the tamp ecosystem import from here — never duplicate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


# ── Regex patterns (compiled once) ───────────────────────────────────────────

_OPEN_ENTRY   = re.compile(r"^- (\d{2}:\d{2}) (.+)$")
_DONE_ENTRY   = re.compile(r"^~~(\d{2}:\d{2}) (.+)~~$")
_TAG_CONTEXT  = re.compile(r"@([\w-]+)")
_TAG_ACTION   = re.compile(r"\+([\w-]+)")


# ── Core types ────────────────────────────────────────────────────────────────

@dataclass
class Entry:
    """A single timestamped note entry within a daily log."""

    time:     str              # "HH:MM"
    text:     str              # raw text including tags
    date:     date             # which log this belongs to
    done:     bool = False
    contexts: list[str] = field(default_factory=list)
    actions:  list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.contexts = _TAG_CONTEXT.findall(self.text)
        self.actions  = _TAG_ACTION.findall(self.text)

    @property
    def clean_text(self) -> str:
        """Text with tags stripped."""
        t = _TAG_CONTEXT.sub("", self.text)
        t = _TAG_ACTION.sub("", t)
        return " ".join(t.split())

    @property
    def datetime(self) -> datetime:
        h, m = map(int, self.time.split(":"))
        return datetime(self.date.year, self.date.month, self.date.day, h, m)

    @property
    def age_days(self) -> int:
        return (date.today() - self.date).days

    def to_line(self) -> str:
        if self.done:
            return f"~~{self.time} {self.text}~~"
        return f"- {self.time} {self.text}"

    @classmethod
    def parse(cls, line: str, log_date: date) -> Entry | None:
        """Parse a single line from a daily log. Returns None if not an entry."""
        m = _OPEN_ENTRY.match(line)
        if m:
            return cls(time=m.group(1), text=m.group(2), date=log_date, done=False)
        m = _DONE_ENTRY.match(line)
        if m:
            return cls(time=m.group(1), text=m.group(2), date=log_date, done=True)
        return None


@dataclass
class DailyLog:
    """A single day's log file: ~/Notes/daily/YYYY-MM-DD.md"""

    date:    date
    path:    Path
    entries: list[Entry] = field(default_factory=list)
    _lines:  list[str]   = field(default_factory=list, repr=False)

    @property
    def open_signals(self) -> list[Entry]:
        return [e for e in self.entries if not e.done and e.actions]

    @property
    def todos(self) -> list[Entry]:
        return [e for e in self.entries if not e.done and "todo" in e.actions]

    @classmethod
    def from_path(cls, path: Path) -> DailyLog:
        log_date = date.fromisoformat(path.stem)
        lines    = path.read_text(encoding="utf-8").splitlines()
        entries  = []
        for line in lines:
            entry = Entry.parse(line, log_date)
            if entry:
                entries.append(entry)
        return cls(date=log_date, path=path, entries=entries, lines=lines)

    def write(self) -> None:
        """Reconstruct and write the file, preserving non-entry lines.

        Walks _lines and self.entries in lockstep — entries are always
        in the same order as they were parsed from the file. Avoids the
        dict-key approach which silently drops duplicate (time, text) pairs.
        """
        entry_iter  = iter(self.entries)
        out_lines: list[str] = []
        for line in self._lines:
            if Entry.parse(line, self.date) is not None:
                try:
                    out_lines.append(next(entry_iter).to_line())
                except StopIteration:
                    out_lines.append(line)   # safety: more lines than entries
            else:
                out_lines.append(line)

        self.path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    # Allow DailyLog to be initialised with lines= kwarg cleanly
    def __init__(
        self,
        date:    date,
        path:    Path,
        entries: list[Entry] | None = None,
        lines:   list[str]   | None = None,
    ) -> None:
        self.date    = date
        self.path    = path
        self.entries = entries or []
        self._lines  = lines   or []


@dataclass
class Note:
    """A thematic note: ~/Notes/notes/<name>.md"""

    name:    str
    path:    Path

    @property
    def title(self) -> str:
        return self.name.replace("-", " ").replace("_", " ")

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def write(self, content: str) -> None:
        self.path.write_text(content, encoding="utf-8")


@dataclass
class JournalEntry:
    """A journal prose entry: ~/Notes/daily/YYYY-MM-DD-journal.md"""

    date: date
    path: Path

    def read(self) -> str:
        if self.path.exists():
            return self.path.read_text(encoding="utf-8")
        return ""

    def write(self, content: str) -> None:
        self.path.write_text(content, encoding="utf-8")

    @property
    def exists(self) -> bool:
        return self.path.exists()
