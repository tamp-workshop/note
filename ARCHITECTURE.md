# tamp • Architecture

This document explains the design decisions behind tamp and tamp-note:
what we built, what we rejected, and why. It is written for anyone who
wants to deeply understand the codebase before changing it to make it their own or who is curious about the reasoning behind the structure.

---

## The core constraint: plain files

Every architectural decision traces back to one constraint:

> The user's data must be readable and editable without tamp, forever.

This sounds simple but has real consequences. It rules out:

- Binary formats, databases, or any proprietary storage
- Metadata embedded in the tool (tags, completion state, IDs)
- Any format that requires tamp to be installed to read

Everything lives in plain markdown. The entry format `- HH:MM text`
and `~~HH:MM text~~` is readable in any text editor and greppable from
the shell. The schema is documented in `SCHEMA.md` and versioned so any
future tool knows what it's reading.

---

## Why a monorepo

tamp started as a single script. It grew, and early versions mixed
concerns that should have been separate: the data layer, the UI, the
statistics engine, and the command handlers all lived together.

The monorepo split was driven by a concrete need: we wanted a second tool
(`tamp-task`) that reads the same files as `tamp-note`. The choices were:

1. **Duplicate the file-reading logic** *clearly wrong. Two codebases
   that parse the same format will diverge.*

2. **Make tamp-note a library** *awkward. A TUI tool is not a good API.*

3. **Extract a shared core** *the right answer. `tamp-core` owns all
   data access. Every tool imports from it. Nothing else touches files.*

This is why `tamp-core` exists as a separate package. It has no UI
dependencies, no CLI, and no opinion about how data is displayed. It is
purely a data layer.

---

## tamp-core: the data layer

`tamp-core` contains four things:

**Models** (`models.py`) *dataclasses for `Entry`, `DailyLog`, `Note`,
and `JournalEntry`. These are the only data structures in the system.
All tools speak in these types. Parsing lives here — one place,
one implementation.*

**Corpus** (`corpus.py`) *the single point of access for `~/Notes/`.
All reads and writes go through `Corpus`. No other code touches the
filesystem directly. This makes the data layer testable in isolation
and means the directory structure can change without touching the tools.*

**Config** (`config.py`) *reads and writes `~/.tamp-note/config.toml`.
Holds derived paths (`daily_dir`, `journal_dir`, `notes_subdir`) so
no tool hardcodes a path.*

**Stats** *(`stats.py`) local statistical analysis. Kept in core
because it operates purely on `Corpus` data and has no UI concerns.
The analysis is designed with a cold-start threshold: pattern inference
does not activate until there are at least 14 days of history, to avoid
producing noise from sparse data.*

---

## tamp-note: the TUI tool

`tamp-note` is built on [Textual](https://github.com/Textualize/textual).
It has three layers:

**CLI** (`cli.py`) *the entry point. Handles quick-add (`note "text"`),
stdin (`note -`), migration, and version. Launches the TUI for interactive
sessions. This layer is deliberately thin and it does no data work itself.*

**Commands** (`commands.py`) *every slash command is a plain function
with the signature `(Corpus, list[str]) -> CommandResult`. The registry
(`REGISTRY`) maps names to command descriptors. `dispatch()` parses and
routes a raw string like `"/find @dev"`.*

This structure means:
- Commands are easy to test without a running TUI
- Adding a command is two steps: write the function, register it
- The TUI is not coupled to command logic — it receives a `CommandResult`
  and acts on it

**App** (`app.py`) *the Textual application. Owns layout, routes input,
delegates to command handlers. Keeps no business logic itself.*

---

## The TUI layout decision

The layout went through several iterations. The final structure is:

```
WelcomePanel    height: auto
RichLog         height: 1fr   ← fills all remaining space
InputBar        height: 3
HelpPanel       height: auto, display: none/block
CommandPalette  height: auto, display: none/block
TagHints        height: auto, display: none/block
HintBar         height: 1
StatusBar       height: 1
```

The key decision: **palette and help panels live below the input in normal
DOM flow**, toggled with a CSS class (`open` → `display: block`, no class
→ `display: none`). When they appear they push the hint and status lines
down and that is expected and correct.

Earlier versions used Textual's overlay/layer system to float the palette
above the input. This was rejected because:

- It required CSS offset arithmetic (`offset: 0 -6`) that broke at
  different terminal sizes
- Overlay positioning in Textual is less predictable than normal flow
- The resulting code was harder to read and reason about

The normal-flow approach is simpler, more robust, and easier to maintain.

---

## Key interception: why `_on_key`

`NoteInput` uses `_on_key` (a Textual private method) to intercept `?`
and `q` when the field is empty.

We use a private method deliberately, with this reasoning:

`App.on_key` fires *after* the `Input` widget has already processed the
keystroke. By the time the App sees it, `?` is already in the field.
The only reliable interception point is inside the widget's own key
handler, before it calls `super()._on_key(event)`.

`_on_key` has been stable from Textual 0.60 through 0.80. We document
the dependency explicitly in the code and will update it if the method
signature changes.

`/` is intentionally *not* intercepted this way. The slash appears in the
field and the palette filters live via `on_input_changed`. This means the
user can type `/find query` manually and press Enter without ever touching
the palette. The palette is progressive enhancement, not a gate.

---

## Tag hints: why no IDs on label nodes

The `TagHints` widget repopulates its child labels every time the user
types a new character after `@` or `+`. Early versions used IDs on each
label (e.g. `id="th-todo"`) for targeting during highlight updates.

This caused a `DuplicateIds` error. The reason: `remove_children()` in
Textual is async as it queues the removal. If `mount()` runs before the
removal completes, the old label is still in the node tree and the new
one collides with it.

The fix has two parts:
1. Remove children synchronously via `self.query(Label)` + `.remove()`
2. Drop IDs from hint labels entirely. Highlight by index position
   instead

This is more robust and simpler. Index-based highlighting cannot produce
ID collisions.

---

## CommandResult: why a return type

Command handlers return `CommandResult` rather than writing to the UI
directly. This is a deliberate boundary.

If commands wrote to the log themselves, they would need a reference to
the TUI, coupling business logic to the display layer. Instead, commands
return a plain dataclass. The TUI decides what to do with it.

`CommandResult` has four fields:
- `output`: text to display
- `kind`: how to display it (`info`, `success`, `error`, `table`, `todo_list`)
- `data`: structured payload (e.g. a `list[Entry]` for the todo modal)
- `action`: a side effect for the TUI (`open_editor:<path>`, `exit`)

The `todo_list` kind is special: the TUI intercepts it and opens an
interactive `TodoScreen` modal rather than printing text. The command
itself doesn't know this. It just returns the data.

---

## What we decided not to build (yet)

**Plugin system** *we considered a hook architecture for commands so
third-party tools could register them. We deferred this until `tamp-task`
exists and we understand what the inter-tool API actually needs to be.
A premature plugin system would just be abstraction without a use case.*

**Natural language date parsing** *`/last week`, `/find yesterday`.
Tempting but a rabbit hole. The corpus query API is clean and the
scope creep risk is real. Deferred.*

**Cloud sync** *explicitly out of scope. The whole point is local files.
If you want sync, use a folder that is already synced (Dropbox, iCloud,
a git repo). tamp does not need to know about it.*

**`+todo` external sync** *entries tagged `+todo` show up in the todo
list. We considered syncing them to an external task manager (Things,
Linear, etc.). This belongs in `tamp-task`, not `tamp-note`. The concern
of `tamp-note` is capture and triage. Mixing them would blur both tools.*

---

## Testing philosophy

Tests live in `packages/tamp-note/tests/`. They test `tamp-core` logic
almost exclusively: corpus operations, entry parsing, command dispatch,
statistics. The TUI is not tested at the widget level because:

- Textual provides its own testing framework (`App.run_test()`) which
  we have not yet integrated
- The logic worth testing (data access, command handling) is already
  decoupled from the TUI
- The TUI is thin. It routes and renders, it does not compute

This is a deliberate tradeoff. When the codebase stabilises, TUI integration tests are the right next step.
