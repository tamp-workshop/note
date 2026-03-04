# tamp v0.8.0

> Small tools for people who think in plain text.

tamp is a collection of command-line tools built around a single idea:
your notes, tasks, and thoughts should live in plain markdown files
that you own, on your machine, forever.

No app. No subscription. No account. No sync service that goes away.
Just files, a schema, and small tools that read and write them.

---

## The idea

Most tools ask you to trust them with your data.
You log in, you sync, you export and one day the app pivots,
the company folds, or the pricing changes.

tamp works differently. Your data is yours.

All files gather in `Notes`, but many of you might want to change the default behaviour in the config files.

```
~/Notes/
├── daily/      timestamped entries, one file per day
├── notes/      thematic notes, plain markdown
├── journal/    prose journal entries
└── archive/    anything moved out of the way
```

Every file is readable without tamp. Every file is editable without tamp.
tamp is a lens on your data, not a lock.

---

## Tools

### tamp-note

The daily capture and triage tool.

```sh
note "fix the parser edge case @dev +todo"
note
```

Quick-add from anywhere. A full TUI when you need to think.
Local statistics that notice patterns without making noise.

→ [packages/tamp-note](./packages/tamp-note)

### tamp-task *(planned)*

Todo and action management across your corpus.
Reads the same files as tamp-note, no duplications.

### tamp-insight *(planned)*

Deeper statistical analysis and weekly summaries.
Still local, still no API calls.

---

## Why I changed course

tamp started as a single-file script. It grew quickly, and early versions
tried to do too much in one place. Too many ideas didn't work with the sleek terminal commands I wanted to build at first. So now, we have a monolithic tool that mixed capture, search, statistics, and task management into one messy binary.

The rewrite separates concerns cleanly:

- **tamp-core** *shared data models, corpus access, statistics engine.
  Every tool imports from here. No tool reads files directly.*

- **tamp-note** *the capture and triage TUI. Fast. Keyboard-driven.
  Does one thing well.*

- **Future tools** *built on tamp-core, so they speak the same schema
  without duplicating logic.*

The schema is also now versioned and documented. Any tool that reads
`~/Notes/` should declare which schema version it supports.

---

## The schema

All tools share the same file format, documented in
[SCHEMA.md](./SCHEMA.md).

Entries look like this:

```
- 09:14 fix the parser edge case @dev +todo
- 10:02 read SICP chapter 4 @dev +read
~~09:14 fix the parser edge case @dev +todo~~
```

`@word` is a context. `+word` is an action. A strikethrough line is done.
That's the whole format. Grep-friendly. Human-readable. Stable.

---

## Principles

**Plain files, always.**
Nothing in tamp writes a format you can't read with `cat`.

**Local by default.**
Statistics, patterns, search, ... all computed locally.
Nothing is sent anywhere.

**Small tools, sharp edges.**
Each tool has a clear scope. When a tool grows beyond that scope,
it becomes two tools.

**Own your data.**
If you stop using tamp tomorrow, your notes are still there,
readable in any text editor, searchable with `grep`.

---

## Development

tamp is a monorepo managed with [uv](https://github.com/astral-sh/uv).

```sh
git clone https://github.com/tamp-workshop/tamp
cd tamp
uv sync
uv run pytest
```

```
tamp/
├── packages/
│   ├── tamp-core/     shared library (models, corpus, config, stats)
│   └── tamp-note/     the TUI tool
├── SCHEMA.md          file format specification
└── README.md          this file
```

---

## Status

`tamp-note` is actively used and maintained.
`tamp-task` and `tamp-insight` are in design.

Issues and ideas welcome.
