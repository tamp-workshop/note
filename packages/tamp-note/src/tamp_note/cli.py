"""
tamp_note.cli
~~~~~~~~~~~~~
Entry point for the `tamp-note` command (aliased as `note`).

  note                     → interactive session
  note "thought here"      → quick-add and exit
  note -                   → read from stdin
  note migrate             → migrate flat ~/Notes/ to daily/ + notes/
  note version             → print version
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    args = sys.argv[1:]

    # ── Version ────────────────────────────────────────────────────────────
    if args and args[0] in ("version", "--version", "-v"):
        print("tamp-note 0.8.0")
        return

    # ── Migration ──────────────────────────────────────────────────────────
    if args and args[0] == "migrate":
        _run_migration()
        return

    from tamp_core import Config, Corpus

    config = Config.load()
    corpus = Corpus(config)

    # ── stdin quick-add ───────────────────────────────────────────────────
    if args and args[0] == "-":
        text = sys.stdin.read().strip()
        if text:
            entry = corpus.append_entry(text)
            print(f"  {entry.time}  {entry.text}")
        return

    # ── Quick-add: note "thought here" ─────────────────────────────────────
    if args:
        text = " ".join(args)
        entry = corpus.append_entry(text)
        print(f"  → {entry.time}  {entry.text}")
        return

    # ── First-run name setup ───────────────────────────────────────────────
    if not config.name:
        print("\n  tamp-note — first run\n")
        name = input("  What should tamp-note call you? ").strip()
        if name:
            config.name = name
            config.save()
            print(f"\n  Got it. Welcome, {name}.\n")

    # ── Interactive session ────────────────────────────────────────────────
    _run_session(config, corpus)


def _run_session(config, corpus) -> None:
    try:
        from .app import TampNoteApp
        app = TampNoteApp(config=config, corpus=corpus)
        app.run()
    except ImportError as e:
        print(f"tamp-note: TUI dependencies missing — {e}")
        print("  run: uv pip install textual")
        sys.exit(1)


def _run_migration() -> None:
    from tamp_core import Config, Corpus

    config = Config.load()
    corpus = Corpus(config)
    source = Path(input(
        f"  source directory to migrate from [{config.notes_dir}]: "
    ).strip() or str(config.notes_dir))

    if not source.exists():
        print(f"  not found: {source}")
        sys.exit(1)

    flat_mds = list(source.glob("*.md"))
    if not flat_mds:
        print("  no .md files found in source directory.")
        return

    print(f"\n  found {len(flat_mds)} markdown files in {source}/")
    print(f"  → daily logs  →  {config.daily_dir}/")
    print(f"  → thematic    →  {config.notes_subdir}/")
    confirm = input("\n  proceed? [y/n] ").strip().lower()
    if confirm != "y":
        print("  aborted.")
        return

    migrated = corpus.migrate_flat(source)
    print(f"\n  migrated {len(migrated)} files.")
    for p in migrated:
        print(f"  ✓ {p.name}")
