# tamp-note

> Daily notes, plain and simple.

Open a terminal. Type a thought. Done.

tamp-note is a capture-and-triage tool for people who live in the terminal.
All your data is plain markdown in a folder you own. There's no app, no account,
no sync service.

---

## Install

```sh
uv pip install tamp-note
```

Recommended alias:

```sh
# ~/.zshrc or ~/.bashrc
alias note='tamp-note'
```

---

## Quick-add

The fastest path: one command, one thought, done.

```sh
note "fix the parser edge case @dev +todo"
note "look into harfbuzz @design +read"
echo "piped from somewhere" | note -
```

Appends a timestamped entry to today's log and exits immediately.

---

## Interactive session

```sh
note
```

A full TUI opens. The welcome panel shows your open todos and anything
overdue. Type freely to add notes. Use `/` for commands.

```
╭── tamp-note  v0.8 ──────────────────────────────────────────────────╮
│  Welcome back, Tim.             Today                               │
│  Wednesday, 4 March 2026         · fix the parser edge case  2d     │
│  12 logs · 4 today               · look into harfbuzz               │
╰─────────────────────────────────────────────────────────────────────╯

  > type a note, or /command
  ? help   / commands   ctrl+d quit
```

---

## Commands

Type `/` to open the command palette. Type to filter. Arrow keys to
navigate. Enter to run.

| Command | What it does |
|---|---|
| `/todo` | Interactive todo checklist, sorted by age |
| `/find <query>` | Full-text search across all entries |
| `/last [n]` | Last n entries (default 10) |
| `/journal` | Open today's journal in `$EDITOR` |
| `/journal rename <name>` | Rename the journal file |
| `/tags` | Tag overview with counts |
| `/stats` | Corpus statistics and patterns |
| `/ls` | Notes folder overview |
| `/notes` | List thematic notes |
| `/open <n>` | Open or create a note |
| `/new <n>` | Create a new note |
| `/rename <old> <new>` | Rename a note |
| `/delete <n>` | Delete a note |
| `/config` | Open config in `$EDITOR` |
| `/help` | Commands and keybinding reference |

---

## Tags

```sh
note "dentist appointment @health +todo"
note "interesting paper on transformers @ml +read"
note "new font release @design +idea"
```

`@word` marks context. `+word` marks action type.
Free-form, composable, grep-friendly.

Tag autocomplete: type `@` or `+` while writing to see known tags.

**Common conventions** (advisory, not enforced):

| Tag | Meaning |
|---|---|
| `+todo` | Actionable task |
| `+read` | Something to read |
| `+idea` | Idea to explore |
| `+follow-up` | Needs follow-up |
| `@dev` | Development context |
| `@design` | Design context |
| `@health` | Health / personal |

---

## Keyboard shortcuts

| Key | Action |
|---|---|
| `?` | Toggle help panel |
| `/` | Open command palette |
| `↑` / `↓` | Command history |
| `Tab` | Autocomplete tag or command |
| `ctrl+r` | Jump to `/find` |
| `ctrl+d` | Quit |
| `q` | Quit (when input is empty) |

---

## Journal

```sh
note
/journal
```

Opens today's journal file in `$EDITOR`, pre-filled with the date and
your open todos as reference.

Journal entries live in `~/Notes/journal/YYYY-MM-DD.md`, separate from
the daily log. To rename a journal file from inside tamp-note:

```
/journal rename 2026-03-04-reflection
```

---

## Statistics

```sh
/stats
```

Local analysis of your corpus. Pattern analysis activates after 14 days
of history. Nothing is sent anywhere and everything runs on your machine.

Tracks: entry volume, peak hours, tag frequencies, completion rates,
open todo trends, active streaks.

---

## File structure

```
~/Notes/
├── daily/
│   ├── 2026-03-04.md      timestamped entries
│   └── 2026-03-05.md
├── journal/
│   └── 2026-03-04.md      prose journal entries
├── notes/
│   └── fonts.md            thematic notes
└── archive/
```

Plain markdown. Edit directly. Move files around.

---

## Config

`~/.tamp-note/config.toml` created on first run, edit with `/config`.

```toml
name          = "Tim"
notes_dir     = "~/Notes"
editor        = ""          # falls back to $VISUAL, $EDITOR, vi
theme         = "vanguard-outpost"
stats_enabled = true
quote_on_done = true
```

---

## Migration from v1

v1 kept journal entries alongside daily logs as `YYYY-MM-DD-journal.md`.
v2 moves them to a dedicated `journal/` folder.

```sh
tamp-note migrate
```

Or move the files manually. They're just markdown.

---

## Part of tamp

tamp-note is one tool in the [tamp](https://github.com/tamp-workshop/tamp)
ecosystem. All tools share the same file format and data layer.
Your notes work with all of them, and with none of them.
