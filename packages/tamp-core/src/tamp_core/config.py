"""
tamp_core.config
~~~~~~~~~~~~~~~~
Reads and writes ~/.tamp-note/config.toml.
Every tamp tool imports Config from here.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


CONFIG_DIR  = Path.home() / ".tamp-note"
CONFIG_FILE = CONFIG_DIR / "config.toml"

_TEMPLATE = """\
# tamp-note configuration
# Edit freely. Delete this file to reset to defaults.

config_version = {config_version}

# Your name — shown on the welcome screen
name = "{name}"

# Where your notes live
notes_dir = "{notes_dir}"

# Editor used for /journal, /open, /new, /config
# Leave empty to use $VISUAL or $EDITOR from your environment
editor = "{editor}"

# Colour theme: vanguard-outpost
theme = "{theme}"

# Local-only statistical analysis of your corpus
stats_enabled = {stats_enabled}

# Motivational quote when you complete a todo
quote_on_done = {quote_on_done}
"""


@dataclass
class Config:
    config_version: int  = 1
    name:           str  = ""
    notes_dir:      Path = field(default_factory=lambda: Path("~/Notes").expanduser())
    editor:         str  = ""
    theme:          str  = "vanguard-outpost"
    stats_enabled:  bool = True
    quote_on_done:  bool = True

    # ── Derived paths ─────────────────────────────────────────────────────────

    @property
    def daily_dir(self) -> Path:
        return self.notes_dir / "daily"

    @property
    def notes_subdir(self) -> Path:
        return self.notes_dir / "notes"

    @property
    def journal_dir(self) -> Path:
        # Journal entries live in ~/Notes/journal/YYYY-MM-DD.md
        return self.notes_dir / "journal"

    @property
    def archive_dir(self) -> Path:
        return self.notes_dir / "archive"

    @property
    def display_name(self) -> str:
        return self.name if self.name else "there"

    # ── Load / save ───────────────────────────────────────────────────────────

    @classmethod
    def load(cls) -> Config:
        if not CONFIG_FILE.exists():
            cfg = cls()
            cfg.save()
            return cfg

        with open(CONFIG_FILE, "rb") as f:
            raw = tomllib.load(f)

        return cls(
            config_version = raw.get("config_version", 1),
            name           = raw.get("name", ""),
            notes_dir      = Path(raw.get("notes_dir", "~/Notes")).expanduser(),
            editor         = raw.get("editor", ""),
            theme          = raw.get("theme", "vanguard-outpost"),
            stats_enabled  = raw.get("stats_enabled", True),
            quote_on_done  = raw.get("quote_on_done", True),
        )

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        content = _TEMPLATE.format(
            config_version = self.config_version,
            name           = self.name,
            notes_dir      = str(self.notes_dir).replace(str(Path.home()), "~"),
            editor         = self.editor,
            theme          = self.theme,
            stats_enabled  = "true" if self.stats_enabled else "false",
            quote_on_done  = "true" if self.quote_on_done else "false",
        )
        CONFIG_FILE.write_text(content, encoding="utf-8")

    def resolve_editor(self) -> str:
        """Return the editor to use, falling back through env vars to vi."""
        import os
        return (
            self.editor
            or os.environ.get("VISUAL", "")
            or os.environ.get("EDITOR", "")
            or "vi"
        )

    def ensure_dirs(self) -> None:
        """Create the full Notes directory structure on first run."""
        for d in (self.daily_dir, self.notes_subdir, self.journal_dir, self.archive_dir):
            d.mkdir(parents=True, exist_ok=True)
