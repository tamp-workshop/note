# tamp

> Small tools for people who think in plain text.

![Tests](https://github.com/tamp-workshop/tamp/actions/workflows/ci.yml/badge.svg)
![Version](https://img.shields.io/badge/version-v0.8.0-D07878)
![Python](https://img.shields.io/badge/python-3.11+-746E80)
![License](https://img.shields.io/badge/license-MIT-8CA870)

---

## Quick start

```sh
# Install
uv pip install tamp-note

# Recommended alias
echo "alias note='tamp-note'" >> ~/.zshrc

# Quick-add a note
note "fix the parser edge case @dev +todo"

# Open the interactive TUI
note
```

Notes land in `~/Notes/daily/YYYY-MM-DD.md` as plain markdown. No account, no sync service, no lock-in.

---

## What works now

**Quick-add** — `note "text"` appends a timestamped entry and exits immediately.

**Interactive TUI** — `note` opens a full terminal interface. Type to add notes. `/` for commands.

**Slash commands** — `/todo`, `/find <query>`, `/last`, `/journal`, `/tags`, `/stats`, `/open`, `/new` and more. Type `/` to browse the command palette.

**Tags** — `@word` for context, `+word` for action type. Autocomplete as you type.

**Journal** — `/journal` opens today's journal in `$EDITOR`, pre-filled with open todos.

**Local statistics** — `/stats` analyses your corpus. Nothing leaves your machine.

---

## Example workflow

```sh
# Morning: quick capture
note "planning call with design team @work +todo"
note "interesting read on parser combinators @dev +read"

# Evening: open TUI to triage
note
> /todo          # interactive todo list
> /last 5        # last 5 entries
> /journal       # open today's journal in $EDITOR
```

---

## File structure

```
~/Notes/
├── daily/       YYYY-MM-DD.md   — timestamped entries
├── journal/     YYYY-MM-DD.md   — prose journal entries
├── notes/       *.md            — thematic notes
└── archive/
```

Plain markdown. Edit directly, grep them, move them around.
tamp is a lens on your data — not a lock.

---

## Install

```sh
uv pip install tamp-note
```

Requires Python 3.11+. Uses [uv](https://github.com/astral-sh/uv) for package management.

---

## Development

```sh
git clone https://github.com/tamp-workshop/tamp
cd tamp
uv sync
uv run pytest
```

```
tamp/
├── packages/
│   ├── tamp-core/     shared data layer (models, corpus, config, stats)
│   └── tamp-note/     the TUI tool
├── ARCHITECTURE.md    design decisions and tradeoffs
├── CONTRIBUTING.md    how to contribute
├── ROADMAP.md         what's planned and why
└── SCHEMA.md          file format specification
```

---

## Roadmap

See [ROADMAP.md](./ROADMAP.md). Short version:

- **Now** — fix known UI issues, inline `/todo`, improve test coverage
- **Next** — `tamp-task`: task management on the same corpus
- **Later** — `tamp-insight`: weekly statistical digests, local only

---

## Why we changed course

tamp started as a single shell script. The rewrite in March 2026 split it into a proper monorepo so future tools can share the same data layer without duplicating logic. Full story in [ARCHITECTURE.md](./ARCHITECTURE.md).

---

`tamp-note` is actively used and maintained. Issues and ideas welcome.
