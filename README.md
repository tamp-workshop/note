# tamp-note

**Minimal CLI note taking. Part of the tamp CLI toolkit.**

Plain markdown files.
No dependencies beyond standard Unix tools.
Works on macOS and Linux.

---

## Install

```sh
curl -o /usr/local/bin/tamp-note https://raw.githubusercontent.com/tamptools/note/main/note.sh
chmod +x /usr/local/bin/tamp-note
```

Or clone and symlink:

```sh
git clone https://github.com/tamp/note.git
ln -s "$(pwd)/tamp-note/tamp-note.sh" /usr/local/bin/tamp-note
```

**Recommended:** add an alias for daily use:

```sh
# ~/.zshrc or ~/.bashrc
alias note='tamp-note'
```

---

## Usage

```sh
tamp-note "your idea"         # Append a timestamped entry to today's log
tamp-note                     # Open today's log in $EDITOR
tamp-note open fonts          # Open/create ~/Notes/fonts.md (thematic note)
tamp-note find "parser"       # Search across all notes (case-insensitive)
tamp-note todo                # List all open +todo items with source file and line
tamp-note done "parser bug"   # Mark matching +todo as done
tamp-note last [n]            # Show last n entries with source date (default: 10)
tamp-note tags                # List all @context and +action tags with counts
tamp-note help                # Show usage
```

---

## Tags

Tags are plain text. Grep-friendly. No special syntax.

| Tag | Purpose |
|-----|---------|
| `@dev` `@design` `@music` | Context — retrieve with `tamp-note find @dev` |
| `+todo` | Actionable — surfaced by `tamp-note todo` |
| `+read` `+idea` `+follow-up` | Other action types |

```sh
tamp-note "look into Harfbuzz shaping for variable fonts @design +todo"
```

Use `tamp-note tags` to see all tags currently in use across your notes, with counts:

```
--- tags in use ---

@context
  @dev                    12
  @design                  5
  @music                   2

+action
  +todo                    8
  +idea                    4
  +read                    1
```

---

## Marking todos done

`tamp-note done` finds the matching line and wraps it in markdown strikethrough:

```sh
tamp-note done "Harfbuzz"
# ✔  marked done in 2026-02-25.md
```

The line becomes `- ~~09:14 look into Harfbuzz...~~` and is excluded from future `tamp-note todo` output.

---

## File structure

```
~/Notes/
  2026-02-25.md       # daily log (auto-created)
  2026-02-24.md
  fonts.md            # thematic note  (tamp-note open fonts)
  compilers.md
```

Daily logs are plain Markdown:

```markdown
# Tuesday, February 25 2026

- 09:14 look into Harfbuzz shaping for variable fonts @design +todo
- 11:42 cache invalidation idea for the parser @dev +idea
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NOTES_DIR` | `~/Notes` | Where notes are stored |
| `EDITOR` | `vim` | Editor used by `tamp-note` and `tamp-note open` |

```sh
export NOTES_DIR="$HOME/Notes"
export EDITOR="nvim"
```

---

## Shell quirks

**zsh:** The `!` character triggers history expansion inside double quotes, causing the prompt to hang:

```sh
note "Hello notes!"   # ❌ hangs in zsh
note 'Hello notes!'   # ✔ use single quotes instead
```

To disable this behaviour permanently, add to your `~/.zshrc`:

```sh
setopt NO_BANG_HIST
```

---

## About tamp

Small tools. Only necessary parts.

---

## Contributing

Intentionally small. Good contributions: bug fixes, shell compatibility, new subcommands that follow the same minimal philosophy. Please don't add dependencies.

---

## License

MIT
