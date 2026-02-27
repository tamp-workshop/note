# tamp-note

> Daily notes, plain and simple.

Open a terminal. Type a thought. Close the terminal. That's the whole workflow.

No app to open. No account to create. No proprietary format that holds your notes hostage five years from now. Just markdown files in a folder you own, timestamped and tagged, findable with a single command.

Your future self will know where to look. Or not, who cares.

---

## Install

```sh
curl -o /usr/local/bin/tamp-note https://raw.githubusercontent.com/tamp-workshop/note/main/note
chmod +x /usr/local/bin/tamp-note
```

Or clone and symlink:

```sh
git clone https://github.com/tamp-workshop/note.git
ln -s "$(pwd)/note/note" /usr/local/bin/tamp-note
```

**Recommended alias**: because `tamp-note` is a lot to type at 9am:

```sh
# ~/.zshrc or ~/.bashrc
alias note='tamp-note'
```

---

## Usage

```sh
tamp-note "your thought here"     # append a timestamped entry to today's log
tamp-note                         # open today's log in $EDITOR
tamp-note open fonts              # open or create ~/Notes/fonts.md
tamp-note find "parser"           # search across all notes
tamp-note todo                    # list all open +todo items
tamp-note done "parser bug"       # mark matching +todo as done
tamp-note last [n]                # show last n entries (default: 10)
tamp-note tags                    # all tags in use, with counts
tamp-note help                    # the full picture
```

---

## Tags

Tags are plain text. No special syntax. Completely grep-friendly.

| Tag | Purpose |
|-----|---------|
| `@dev` `@design` `@music` | Context → where does this belong? |
| `+todo` | Something to act on |
| `+read` `+idea` `+follow-up` | Other action types |

```sh
tamp-note "look into Harfbuzz shaping for variable fonts @design +todo"
```

`tamp-note tags` shows everything in use across your notes, with counts. Useful for noticing that you have forty-three `+todo` items and have done none of them. Motivating, in its own way.

---

## Marking todos done

```sh
tamp-note done "Harfbuzz"
# ✔  marked done in 2026-02-25.md
```

The line becomes `~~09:14 look into Harfbuzz...~~`. Struck through in markdown, excluded from future `tamp-note todo` output. Visible history, not silent deletion.

---

## File structure

Notes live in plain markdown files. Yours, forever.

```
~/Notes/
  2026-02-25.md       # today's log → auto-created on first entry
  2026-02-24.md
  fonts.md            # thematic note (tamp-note open fonts)
  compilers.md
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NOTES_DIR` | `~/Notes` | Where notes live |
| `EDITOR` | `vim` | Editor for `tamp-note` and `tamp-note open` |

---

## One zsh quirk worth knowing

The `!` character triggers history expansion inside double quotes:

```sh
note "Ship it!"   # ❌ hangs in zsh
note 'Ship it!'   # ✔  single quotes are your friend
```

Or add `setopt NO_BANG_HIST` to your `~/.zshrc` and forget this ever came up.

---

## Part of tamp

A considered working environment for programmers who care.  
[github.com/tamp-workshop](https://github.com/tamp-workshop) · MIT License
