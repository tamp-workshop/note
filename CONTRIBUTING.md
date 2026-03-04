# Contributing to tamp

Thanks for your interest. This document covers how to set up, run tests,
and submit changes. For the reasoning behind the architecture, read
[ARCHITECTURE.md](./ARCHITECTURE.md) first — it will save you time.

---

## Setup

tamp uses [uv](https://github.com/astral-sh/uv) for package management.

```sh
git clone https://github.com/tamp-workshop/tamp
cd tamp
uv sync
```

That installs all dependencies including dev dependencies (`pytest`).

---

## Running tests

```sh
uv run pytest
```

All tests are in `packages/tamp-note/tests/`. They run against
`tamp-core` — corpus operations, entry parsing, command dispatch,
statistics. No TUI tests yet (see ARCHITECTURE.md for why).

Before opening a PR, make sure all tests pass and no new ones are
skipped.

---

## Project structure

```
tamp/
├── packages/
│   ├── tamp-core/
│   │   └── src/tamp_core/
│   │       ├── __init__.py    exports Config, Corpus, welcome_signals
│   │       ├── models.py      Entry, DailyLog, Note, JournalEntry
│   │       ├── corpus.py      all filesystem access goes here
│   │       ├── config.py      config load/save, derived paths
│   │       └── stats.py       local corpus analysis
│   └── tamp-note/
│       ├── src/tamp_note/
│       │   ├── app.py         Textual TUI
│       │   ├── cli.py         entry point, quick-add, migration
│       │   ├── commands.py    slash command registry and handlers
│       │   └── quotes.py      completion quotes
│       └── tests/
│           └── test_core.py
├── ARCHITECTURE.md
├── CONTRIBUTING.md  ← you are here
├── SCHEMA.md
└── README.md
```

---

## Adding a command

1. Write a handler function in `commands.py`:

```python
def _cmd_mycommand(corpus: Corpus, args: list[str]) -> CommandResult:
    # do something with corpus and args
    return CommandResult(output="result text", kind="info")
```

2. Register it in `REGISTRY` at the bottom of `commands.py`:

```python
Command("mycommand", "short description", "/mycommand", _cmd_mycommand),
```

3. If the command needs user-supplied arguments (e.g. `/open <name>`),
   set `has_args=True`. The palette will drop the command into the input
   field rather than executing immediately.

4. Write a test in `tests/test_core.py`.

That's it. The TUI picks it up automatically.

---

## Code style

**Readability over cleverness.** tamp is meant to be maintained long-term
by people who aren't necessarily its original authors.

- Methods do one thing. If you're writing `and` in a method name, split it.
- Comments explain *why*, not *what*. If the code is obvious, don't comment it.
- No one-liners that chain side effects.
- No `try/except` blocks that silently swallow errors.
- Explicit variable names. `entry` not `e`, `command` not `cmd`,
  unless it's a tight loop where brevity is genuinely clearer.

There is no linter config yet. Use your judgement. When in doubt,
match the style of the surrounding code.

---

## Changing the schema

The file format is defined in `SCHEMA.md` and versioned. If you change
how daily logs, journal entries, or notes are written:

1. Update `SCHEMA.md` with the new format
2. Bump `config_version` in `config.py`
3. Write migration logic in `corpus.py` (`migrate_flat()` is an example)
4. Update the CLI migration command in `cli.py`

Schema changes are breaking changes. We take them seriously.

---

## What belongs in tamp-core vs tamp-note

**tamp-core** — anything that operates on `~/Notes/` files with no UI
dependency. Data models, filesystem access, statistics, config. If a
future tool (`tamp-task`, `tamp-insight`) would also need this logic,
it belongs in core.

**tamp-note** — the TUI, the slash commands, the CLI. Anything that
knows about Textual widgets, keyboard shortcuts, or terminal rendering
belongs here.

If you're unsure, ask: *would a headless script that reads the same files
need this?* If yes, it belongs in core.

---

## Opening a PR

- Keep PRs focused. One concern per PR.
- Write a clear description of what changed and why.
- If you're changing behaviour rather than fixing a bug, open an issue
  first so we can discuss it before you invest time in the implementation.
- Tests for new functionality are expected, not optional.
