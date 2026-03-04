# tamp-note schema

This document defines the file format for tamp-note. All tools in the tamp
ecosystem read and write this format. Changes here require a version bump and
migration tooling.

**Schema version:** 0.8.0

---

## Directory structure

```
~/Notes/                        ← NOTES_DIR (configurable)
├── daily/
│   ├── 2026-03-04.md           ← daily log
│   └── 2026-03-04-journal.md   ← journal entry (optional)
├── notes/
│   ├── fonts.md                ← thematic note
│   └── tamp.md
└── archive/
    └── 2025/
        └── daily/
```

---

## Daily log format

File name: `YYYY-MM-DD.md`

```markdown
# Monday, March 4 2026

- 09:14 fix the parser edge case @dev +todo
- 10:02 read SICP chapter 4 @dev +read
- 11:30 Dwino komt vandaag @food +shopping
~~09:14 fix the parser edge case @dev +todo~~
```

### Entry line

Open entry:
```
- HH:MM <text> [@context...] [+action...]
```

Completed entry (strikethrough):
```
~~HH:MM <text> [@context...] [+action...]~~
```

Rules:
- Lines starting with `- ` followed by `HH:MM` are entries
- Lines starting with `~~` and ending with `~~` are completed entries
- `@word` anywhere in text → context tag
- `+word` anywhere in text → action tag
- Tags are case-sensitive, alphanumeric + hyphens + underscores
- The date header (`# Weekday, Month D YYYY`) is optional but standard
- Non-entry lines (blank lines, other headings) are preserved verbatim

---

## Journal format

File name: `YYYY-MM-DD-journal.md`

Plain markdown prose. No structured format. The file is owned by the user.

```markdown
# March 4, 2026

Long day. Made good progress on the parser. Dwino came by for food...
```

---

## Thematic note format

File name: `<name>.md` in `notes/`

Plain markdown. No structured format. Managed by the user and opened via
`/open <name>` or `note open <name>`.

---

## Config format

File: `~/.tamp-note/config.toml`

```toml
config_version = 1
name            = "Timothy"
notes_dir       = "~/Notes"
editor          = "vi"
theme           = "vanguard-outpost"
stats_enabled   = true
quote_on_done   = true
```

---

## Tag conventions (advisory, not enforced)

| Tag          | Meaning                    |
|--------------|----------------------------|
| `@dev`       | Development / code context |
| `@design`    | Design context             |
| `@health`    | Health / personal          |
| `@food`      | Food / meals               |
| `+todo`      | Actionable task            |
| `+read`      | Something to read          |
| `+idea`      | Idea to explore            |
| `+follow-up` | Follow up needed           |
| `+shopping`  | To buy                     |

Tags are free-form. These are conventions, not constraints.
