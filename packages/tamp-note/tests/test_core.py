"""
Tests for tamp_core — models, corpus, stats.
Run with: pytest tests/
"""

import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
import tempfile
import os


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_notes(tmp_path):
    """A temporary Notes directory with daily/ and notes/ subdirs."""
    (tmp_path / "daily").mkdir()
    (tmp_path / "notes").mkdir()
    (tmp_path / "archive").mkdir()
    return tmp_path


@pytest.fixture
def config(tmp_notes, tmp_path):
    from tamp_core.config import Config
    cfg = Config(
        name       = "Test",
        notes_dir  = tmp_notes,
        stats_enabled = True,
        quote_on_done = False,
    )
    return cfg


@pytest.fixture
def corpus(config):
    from tamp_core.corpus import Corpus
    return Corpus(config)


# ── Entry parsing ─────────────────────────────────────────────────────────────

def test_entry_parse_open():
    from tamp_core.models import Entry
    d = date(2026, 3, 4)
    e = Entry.parse("- 09:14 fix the parser @dev +todo", d)
    assert e is not None
    assert e.time == "09:14"
    assert e.done is False
    assert "dev" in e.contexts
    assert "todo" in e.actions


def test_entry_parse_done():
    from tamp_core.models import Entry
    d = date(2026, 3, 4)
    e = Entry.parse("~~09:14 fix the parser @dev +todo~~", d)
    assert e is not None
    assert e.done is True


def test_entry_parse_non_entry():
    from tamp_core.models import Entry
    d = date(2026, 3, 4)
    assert Entry.parse("# Monday, March 4", d) is None
    assert Entry.parse("", d) is None
    assert Entry.parse("just some text", d) is None


def test_entry_clean_text():
    from tamp_core.models import Entry
    d = date(2026, 3, 4)
    e = Entry.parse("- 09:14 fix the parser @dev +todo", d)
    assert e.clean_text == "fix the parser"


def test_entry_to_line_open():
    from tamp_core.models import Entry
    d = date(2026, 3, 4)
    e = Entry(time="09:14", text="fix the parser @dev +todo", date=d, done=False)
    assert e.to_line() == "- 09:14 fix the parser @dev +todo"


def test_entry_to_line_done():
    from tamp_core.models import Entry
    d = date(2026, 3, 4)
    e = Entry(time="09:14", text="fix the parser @dev +todo", date=d, done=True)
    assert e.to_line() == "~~09:14 fix the parser @dev +todo~~"


# ── Corpus operations ──────────────────────────────────────────────────────────

def test_append_entry(corpus):
    entry = corpus.append_entry("test note @dev +todo")
    assert entry.text == "test note @dev +todo"
    assert "dev" in entry.contexts
    assert "todo" in entry.actions


def test_append_creates_daily_file(corpus, config):
    corpus.append_entry("hello")
    today_path = config.daily_dir / f"{date.today().isoformat()}.md"
    assert today_path.exists()
    content = today_path.read_text()
    assert "hello" in content


def test_open_todos(corpus):
    corpus.append_entry("task one +todo")
    corpus.append_entry("task two +todo")
    corpus.append_entry("just a note")
    todos = corpus.open_todos()
    assert len(todos) == 2


def test_mark_done(corpus):
    corpus.append_entry("fix it +todo")
    todos = corpus.open_todos()
    assert len(todos) == 1

    corpus.mark_done(todos[0])
    todos_after = corpus.open_todos()
    assert len(todos_after) == 0


def test_search(corpus):
    corpus.append_entry("work on the parser @dev")
    corpus.append_entry("buy milk @food")
    results = corpus.search("parser")
    assert len(results) == 1
    assert "parser" in results[0].text


def test_thematic_note_create(corpus, config):
    note = corpus.create_note("fonts")
    assert note.path.exists()
    assert note.name == "fonts"


def test_thematic_note_rename(corpus, config):
    corpus.create_note("fonts")
    corpus.rename_note("fonts", "typography")
    assert (config.notes_subdir / "typography.md").exists()
    assert not (config.notes_subdir / "fonts.md").exists()


def test_tag_counts(corpus):
    corpus.append_entry("note @dev +todo")
    corpus.append_entry("another @dev +read")
    counts = corpus.tag_counts()
    assert counts.get("@dev", 0) == 2
    assert counts.get("+todo", 0) == 1


# ── Stats ─────────────────────────────────────────────────────────────────────

def test_stats_cold_start(corpus):
    from tamp_core.stats import analyse
    # Only 1 log — cold start
    corpus.append_entry("a note")
    stats = analyse(corpus)
    assert stats.has_enough_data is False
    assert stats.total_entries == 1


def test_welcome_signals_empty(corpus):
    from tamp_core.stats import welcome_signals
    signals = welcome_signals(corpus)
    assert signals == []


def test_welcome_signals_with_old_todo(corpus, config):
    """Simulate an old todo by writing a past-dated file directly."""
    from tamp_core.stats import welcome_signals
    from tamp_core.models import Entry

    old_date = date.today() - timedelta(days=10)
    path = config.daily_dir / f"{old_date.isoformat()}.md"
    path.write_text(f"- 09:00 old task +todo\n")

    signals = welcome_signals(corpus)
    assert len(signals) >= 1
    assert "old task" in signals[0].text


# ── Commands ──────────────────────────────────────────────────────────────────

def test_cmd_todo_empty(corpus):
    from tamp_note.commands import dispatch
    result = dispatch(corpus, "/todo")
    assert "clean slate" in result.output


def test_cmd_todo_with_entries(corpus):
    from tamp_note.commands import dispatch
    corpus.append_entry("fix bug +todo")
    result = dispatch(corpus, "/todo")
    assert result.kind == "todo_list"
    assert any("fix bug" in e.text for e in (result.data or []))


def test_cmd_find(corpus):
    from tamp_note.commands import dispatch
    corpus.append_entry("harfbuzz shaping @design")
    result = dispatch(corpus, "/find harfbuzz")
    assert "harfbuzz" in result.output


def test_cmd_unknown(corpus):
    from tamp_note.commands import dispatch
    result = dispatch(corpus, "/unknown")
    assert result.kind == "error"
    assert "unknown" in result.output


def test_cmd_stats(corpus):
    from tamp_note.commands import dispatch
    corpus.append_entry("a note")
    result = dispatch(corpus, "/stats")
    assert "entries" in result.output


def test_cmd_help(corpus):
    from tamp_note.commands import dispatch
    result = dispatch(corpus, "/help")
    assert "/todo" in result.output
    assert "/find" in result.output
