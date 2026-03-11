"""
tamp_note.app
~~~~~~~~~~~~~
Layout (top to bottom, all in normal DOM flow):

    WelcomePanel     height: auto  — amber-bordered header with border_title
    RichLog          height: 1fr   — output, fills all remaining space
    InputBar         height: 3     — "> " + text field
    HelpPanel        height: auto  — shown when ? pressed, hidden otherwise
    CommandPalette   height: auto  — shown when typing /, hidden otherwise
    TagHints         height: auto  — shown when typing @word or +word
    HintBar          height: 1     — static hint line
    StatusBar        height: 1     — last action + open todo count

All three panels (Help, Palette, TagHints) use the same pattern:
  - CSS class "open" → display: block
  - No class        → display: none
  - They live below the input so they push the hint/status lines down when shown

Key design decisions:
  - NoteInput._on_key intercepts ? and q when empty (App.on_key is too late)
  - Palette filter uses .display on Label nodes — no ID manipulation
  - TagHints removes children via query(Label) — NOT remove_children() which is async
  - All colours defined as constants at the top — one place to change
"""

from __future__ import annotations

import os
import subprocess
from datetime import date
from typing import TypeAlias

from textual.app        import App, ComposeResult
from textual.binding    import Binding
from textual.containers import Horizontal, Vertical, Container
from textual.message    import Message
from textual.screen     import ModalScreen
from textual.widgets    import Input, Label, ListItem, ListView, RichLog, Static

from tamp_core        import Config, Corpus, welcome_signals
from tamp_core.models import Entry
from .commands        import REGISTRY, CommandResult, dispatch
from .quotes          import get_quote


EntryList: TypeAlias = list[Entry]


# ── Vanguard Outpost colour constants ─────────────────────────────────────────
# Every colour in this file comes from here. One place to change them all.

C_BG     = "#2A1C28"   # screen background
C_PANEL  = "#1E1520"   # slightly darker background for inset areas
C_BORDER = "#3D2B3A"   # structural borders, very dim text
C_DIM    = "#5A4060"   # dim text (palette unselected, tag hints unselected)
C_MID    = "#746E80"   # secondary text (timestamps, dates)
C_TEXT   = "#DDDCE6"   # main body text
C_RED    = "#D07878"   # brand accent (prompt, commands, errors)
C_AMBER  = "#E2B07C"   # highlight accent (welcome border, selected items)
C_GREEN  = "#8CA870"   # success, done state
C_GREY   = "#9890A2"   # neutral info text


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = f"""
Screen {{
    background: {C_BG};
    color: {C_TEXT};
}}

#root {{
    layout: vertical;
    height: 100%;
}}

/* ── Welcome panel ──────────────────────────────────────────────────────────
   Amber border is the signature visual element — matches Claude Code's style.
   border_title is set programmatically in WelcomePanel.on_mount().
*/
#welcome {{
    height: auto;
    border: solid {C_AMBER};
    border-title-color: {C_AMBER};
    border-title-style: bold;
    margin: 1 2 1 2;
    padding: 0 0;
}}
#welcome-inner {{
    layout: horizontal;
    height: auto;
}}
#welcome-left {{
    width: 28;
    padding: 1 2 1 2;
    border-right: solid {C_BORDER};
    height: auto;
}}
#welcome-right {{
    padding: 1 2 1 2;
    width: 1fr;
    height: auto;
}}

/* Text hierarchy inside the welcome panel:
   name (white bold) > date (mid grey) > stat (very dim) */
.w-name    {{ color: {C_TEXT};  text-style: bold; }}
.w-date    {{ color: {C_MID};                     }}
.w-stat    {{ color: {C_BORDER};                  }}
.w-section {{ color: {C_AMBER}; text-style: bold; }}
.w-signal  {{ color: {C_RED};                     }}
.w-clean   {{ color: {C_GREEN};                   }}
.w-todo    {{ color: {C_GREY};                    }}

/* ── Output log ─────────────────────────────────────────────────────────────
   1fr means it takes all space not claimed by fixed-height elements.
*/
#output-wrap {{
    height: 1fr;
    margin: 0 2;
}}
RichLog {{
    background: {C_BG};
    color: {C_TEXT};
    border: none;
    padding: 0 1;
    scrollbar-size: 1 1;
    scrollbar-color: {C_BORDER} {C_BG};
}}

/* ── Input bar ── */
#input-bar {{
    height: 3;
    margin: 0 2 0 2;
    border-top: solid {C_BORDER};
    layout: horizontal;
    align: left middle;
}}
#prompt {{
    color: {C_RED};
    width: auto;
    padding: 0 1 0 0;
}}
NoteInput {{
    background: {C_BG};
    border: none;
    color: {C_TEXT};
    width: 1fr;
}}
NoteInput:focus {{
    border: none;
    background: {C_BG};
}}

/* ── Help panel ─────────────────────────────────────────────────────────────
   Shown when ? is pressed. A static read-only widget — not the log.
   Same open/close pattern as the palette.
*/
#help-panel {{
    display: none;
    height: auto;
    margin: 0 2 0 2;
    background: {C_PANEL};
    border-left: solid {C_BORDER};
    border-right: solid {C_BORDER};
    border-bottom: solid {C_BORDER};
    padding: 1 2;
    color: {C_MID};
}}
#help-panel.open {{
    display: block;
}}

/* ── Command palette ─────────────────────────────────────────────────────────
   Appears below the input while typing /command.
   Unselected rows are dim (readable but not highlighted).
   Selected row is amber + bold — maximum contrast.
   The ">" gutter marker is added/removed via CSS class on the label itself.
*/
#palette {{
    display: none;
    height: auto;
    max-height: 17;
    margin: 0 2 0 2;
    background: {C_PANEL};
    border-left: solid {C_BORDER};
    border-right: solid {C_BORDER};
    border-bottom: solid {C_BORDER};
    padding: 0 0;
    overflow-y: auto;
    scrollbar-size: 1 1;
    scrollbar-color: {C_BORDER} {C_PANEL};
}}
#palette.open {{
    display: block;
}}
.pal-row {{
    height: 1;
    padding: 0 2;
    color: {C_DIM};
}}
.pal-row.selected {{
    color: {C_AMBER};
    text-style: bold;
    background: {C_BORDER};
}}

/* ── Tag hints ── */
#tag-hints {{
    display: none;
    height: auto;
    max-height: 5;
    margin: 0 2 0 2;
    background: {C_PANEL};
    border-left: solid {C_BORDER};
    border-right: solid {C_BORDER};
    border-bottom: solid {C_BORDER};
    padding: 0 1;
}}
#tag-hints.open {{
    display: block;
}}
.hint-row {{
    height: 1;
    color: {C_DIM};
}}
.hint-row.selected {{
    color: {C_GREY};
    text-style: bold;
}}

/* ── Hint bar — one line below all panels ── */
#hint-bar {{
    height: 1;
    margin: 0 3 0 3;
    color: {C_BORDER};
}}

/* ── Status bar ── */
#status-bar {{
    height: 1;
    margin: 0 2 1 2;
    layout: horizontal;
}}
#status-left  {{ color: {C_MID};   width: 1fr;        }}
#status-right {{ color: {C_AMBER}; text-align: right; width: auto; }}

/* ── Todo modal ── */
TodoScreen {{
    align: center middle;
}}
#todo-panel {{
    width: 66;
    height: auto;
    max-height: 28;
    background: {C_PANEL};
    border: solid {C_AMBER};
    border-title-color: {C_AMBER};
    padding: 0;
}}
#todo-list {{
    height: auto;
    max-height: 20;
    background: {C_PANEL};
    border: none;
    scrollbar-size: 1 1;
    scrollbar-color: {C_BORDER} {C_PANEL};
}}
#todo-list > ListItem {{
    background: {C_PANEL};
    padding: 0 2;
    height: 1;
}}
#todo-list:focus > ListItem.--highlight {{
    background: {C_BORDER};
}}
#todo-quote {{
    height: 1;
    padding: 1 2 0 2;
    color: {C_GREEN};
}}
#todo-keys {{
    color: {C_BORDER};
    padding: 0 2 1 2;
    height: 1;
}}
"""


# ── NoteInput ─────────────────────────────────────────────────────────────────

class NoteInput(Input):
    """
    The main text input.

    Intercepts two keys when the field is empty:
      ?   → show/hide the help panel
      q   → quit

    We use _on_key (a Textual private method) because App.on_key fires
    after the Input widget has already consumed the keystroke — too late
    to prevent it from appearing in the field. Stable in Textual 0.60–0.80.
    """

    class SpecialKey(Message):
        """Posted to the App when ? or q is pressed in an empty field."""
        def __init__(self, key: str) -> None:
            super().__init__()
            self.key = key

    def _on_key(self, event) -> None:
        if not self.value and (event.character == "?" or event.key == "q"):
            self.post_message(self.SpecialKey(event.character or event.key))
            event.prevent_default()
            return
        super()._on_key(event)


# ── WelcomePanel ──────────────────────────────────────────────────────────────

class WelcomePanel(Static):
    """
    Compact header at the top of the screen.

    Left column:  user name (bold white) · date (dim) · stats (very dim)
    Right column: section header (amber bold) · content (grey)

    The amber border with "tamp-note" as its title is the main visual
    signature — mirrors the Claude Code welcome panel style.
    """

    def __init__(self, config: Config, corpus: Corpus) -> None:
        super().__init__(id="welcome")
        self.config = config
        self.corpus = corpus

    def on_mount(self) -> None:
        # The border title appears centred in the top border line
        self.border_title = f"[bold {C_RED}]tamp[/bold {C_RED}][{C_MID}]-note[/{C_MID}]  [{C_BORDER}]v0.8[/{C_BORDER}]"

    def compose(self) -> ComposeResult:
        signals  = welcome_signals(self.corpus)
        today    = self.corpus.today()
        n_logs   = len(self.corpus.all_logs())
        weekday  = date.today().strftime("%A")
        date_str = date.today().strftime("%-d %B %Y")

        with Horizontal(id="welcome-inner"):
            with Vertical(id="welcome-left"):
                yield Label(
                    f"[bold]Welcome back, {self.config.display_name}.[/bold]",
                    classes="w-name",
                )
                yield Label(
                    f"[{C_MID}]{weekday}, {date_str}[/{C_MID}]",
                    classes="w-date",
                )
                yield Label(
                    f"[{C_BORDER}]{n_logs} logs · {len(today.entries)} today[/{C_BORDER}]",
                    classes="w-stat",
                    id="stat-label",
                )

            with Vertical(id="welcome-right"):
                if signals:
                    yield Label(f"[{C_AMBER}]Don't forget[/{C_AMBER}]", classes="w-section")
                    for sig in signals[:3]:
                        yield Label(
                            f"[{C_RED}]·[/{C_RED}] [{C_GREY}]{sig.text}[/{C_GREY}]",
                            classes="w-signal",
                        )
                else:
                    todos = self.corpus.open_todos()
                    yield Label(f"[{C_AMBER}]Today[/{C_AMBER}]", classes="w-section")
                    if todos:
                        for t in todos[:4]:
                            age = f"  [{C_BORDER}]{t.age_days}d[/{C_BORDER}]" if t.age_days else ""
                            yield Label(
                                f"[{C_BORDER}]·[/{C_BORDER}] [{C_GREY}]{t.clean_text}[/{C_GREY}]{age}",
                                classes="w-todo",
                            )
                    else:
                        yield Label(
                            f"[{C_GREEN}]No open todos. Clean.[/{C_GREEN}]",
                            classes="w-clean",
                        )


# ── HelpPanel ─────────────────────────────────────────────────────────────────

class HelpPanel(Static):
    """
    A static help reference shown below the input when ? is pressed.
    Pressing ? again, Escape, or any printable key dismisses it.

    This is NOT the log — it is a fixed widget that appears and disappears.
    Two-column layout: commands on the left, keyboard shortcuts on the right.
    """

    # The content is fixed — written once at class definition time.
    # Using Rich markup for colour.
    CONTENT = (
        f"[{C_AMBER}]commands[/{C_AMBER}]"
        f"                                     [{C_AMBER}]keys[/{C_AMBER}]\n"
        f"[{C_RED}]/todo[/{C_RED}]         interactive todo list"
        f"        [{C_RED}]?[/{C_RED}]        this help\n"
        f"[{C_RED}]/find <q>[/{C_RED}]     full-text search"
        f"             [{C_RED}]↑ / ↓[/{C_RED}]   command history\n"
        f"[{C_RED}]/last [n][/{C_RED}]     recent entries"
        f"               [{C_RED}]ctrl+r[/{C_RED}]  jump to /find\n"
        f"[{C_RED}]/status[/{C_RED}]       quick snapshot"
        f"               [{C_RED}]ctrl+d[/{C_RED}]  quit\n"
        f"[{C_RED}]/journal[/{C_RED}]      open today's journal"
        f"         [{C_RED}]q[/{C_RED}]        quit (empty input)\n"
        f"[{C_RED}]/tags [@tag][/{C_RED}]  tag counts, or filter by tag\n"
        f"[{C_RED}]/stats[/{C_RED}]        corpus stats + patterns\n"
        f"[{C_RED}]/open <n>[/{C_RED}]     open or create a thematic note\n"
        f"[{C_RED}]/export [date][/{C_RED}] export entries to file\n"
        f"[{C_RED}]/undo[/{C_RED}]         undo last done-mark or deletion\n"
        f"[{C_RED}]/ls[/{C_RED}]           notes folder overview\n"
        f"\n"
        f"[{C_AMBER}]adding entries[/{C_AMBER}]\n"
        f"[{C_MID}]just type and press enter — no command needed\n"
        f"add +todo to any entry to create a todo   e.g.  call dentist +todo\n"
        f"add +read, +buy, or any +tag to flag for later[/{C_MID}]\n"
        f"\n"
        f"[{C_AMBER}]tags[/{C_AMBER}]\n"
        f"[{C_RED}]@word[/{C_RED}]  context   e.g. @dev @health\n"
        f"[{C_RED}]+word[/{C_RED}]  action    e.g. +todo +read\n"
        f"[{C_MID}]type @ or + while writing to autocomplete known tags[/{C_MID}]"
    )

    def __init__(self) -> None:
        super().__init__(self.CONTENT, id="help-panel")

    def open(self) -> None:
        self.add_class("open")

    def close(self) -> None:
        self.remove_class("open")

    @property
    def is_open(self) -> bool:
        return "open" in self.classes


# ── CommandPalette ────────────────────────────────────────────────────────────

class CommandPalette(Static):
    """
    Inline command list shown below the input when typing /.
    Commands in registry order (most-used first).

    Selection style: amber + bold + background highlight on selected row,
    dim on all others. High contrast — easy to see which item is active.
    """

    def __init__(self) -> None:
        super().__init__(id="palette")
        self._all_commands: list[str] = list(REGISTRY.keys())
        self._visible:      list[str] = list(self._all_commands)
        self._cursor:       int       = 0

    def compose(self) -> ComposeResult:
        for name in self._all_commands:
            desc = REGISTRY[name].description
            yield Label(
                f"  [{C_RED}]/{name}[/{C_RED}]  [{C_DIM}]{desc}[/{C_DIM}]",
                classes="pal-row",
                id=f"pal-{name}",
            )

    def filter(self, partial: str) -> None:
        """Filter to commands starting with partial. Reset cursor to top."""
        partial        = partial.lower()
        self._visible  = [n for n in self._all_commands if n.startswith(partial)]
        self._cursor   = 0
        for name in self._all_commands:
            label         = self.query_one(f"#pal-{name}", Label)
            label.display = name in self._visible
            label.remove_class("selected")
        self._apply_highlight()

    def _apply_highlight(self) -> None:
        """Apply selection styling to the current cursor row."""
        for i, name in enumerate(self._visible):
            label = self.query_one(f"#pal-{name}", Label)
            if i == self._cursor:
                label.add_class("selected")
            else:
                label.remove_class("selected")

    def move_cursor(self, direction: int) -> None:
        if not self._visible:
            return
        self._cursor = (self._cursor + direction) % len(self._visible)
        self._apply_highlight()

    def selected_command(self) -> str | None:
        if not self._visible:
            return None
        return self._visible[self._cursor]

    def open(self) -> None:
        self.add_class("open")

    def close(self) -> None:
        self.remove_class("open")


# ── TagHints ──────────────────────────────────────────────────────────────────

class TagHints(Static):
    """
    Inline tag suggestions shown below the input when typing @word or +word.
    Tags come from corpus.tag_counts() — shows only tags you have used before.
    """

    def __init__(self) -> None:
        super().__init__(id="tag-hints")
        self._tags:   list[str] = []
        self._cursor: int       = 0

    def load(self, tags: list[str]) -> None:
        """
        Replace the tag list with new suggestions.

        Uses query(Label) + remove() rather than remove_children() because
        remove_children() is async — if mount() runs before the removal
        completes, Textual throws DuplicateIds. Querying and removing
        synchronously avoids this entirely.
        """
        for child in list(self.query(Label)):
            child.remove()

        self._tags   = tags
        self._cursor = 0

        for tag in tags:
            self.mount(Label(tag, classes="hint-row"))

        self._apply_highlight()

    def _apply_highlight(self) -> None:
        labels = list(self.query(Label))
        for i, label in enumerate(labels):
            if i == self._cursor:
                label.add_class("selected")
            else:
                label.remove_class("selected")

    def move_cursor(self, direction: int) -> None:
        if not self._tags:
            return
        self._cursor = (self._cursor + direction) % len(self._tags)
        self._apply_highlight()

    def selected_tag(self) -> str | None:
        if not self._tags:
            return None
        return self._tags[self._cursor]

    def open(self) -> None:
        self.add_class("open")

    def close(self) -> None:
        self.remove_class("open")


# ── TodoScreen ────────────────────────────────────────────────────────────────

class TodoScreen(ModalScreen):
    """
    Modal checklist of open todos.

    ↑ / ↓          navigate
    x or space     mark done
    q or Escape    close

    All keys handled at Screen level — the ListView never sees q or Escape.
    """

    def __init__(self, corpus: Corpus, todos: EntryList) -> None:
        super().__init__()
        self.corpus     = corpus
        self.todos      = list(todos)
        self._completed = 0

    def on_mount(self) -> None:
        self.border_title = f"[{C_AMBER}]open todos[/{C_AMBER}]"
        self.query_one("#todo-list", ListView).focus()

    def compose(self) -> ComposeResult:
        with Vertical(id="todo-panel"):
            yield ListView(
                *[self._make_item(t) for t in self.todos],
                id="todo-list",
            )
            yield Label("", id="todo-quote")
            yield Label(
                f"[{C_BORDER}]x / space = done   q / esc = close[/{C_BORDER}]",
                id="todo-keys",
            )

    def _make_item(self, entry: Entry) -> ListItem:
        age   = f"  [{C_BORDER}]{entry.age_days}d[/{C_BORDER}]" if entry.age_days else ""
        label = f"[{C_MID}][ ][/{C_MID}] [{C_TEXT}]{entry.clean_text}[/{C_TEXT}]{age}"
        return ListItem(Label(label), id=f"todo-{id(entry)}")

    def on_key(self, event) -> None:
        if event.key in ("escape", "q"):
            event.stop()
            self.dismiss(self._completed)
        elif event.key in ("x", "space"):
            event.stop()
            self._mark_selected_done()

    def _mark_selected_done(self) -> None:
        lv  = self.query_one("#todo-list", ListView)
        idx = lv.index
        if idx is None or idx >= len(self.todos):
            return

        entry = self.todos[idx]
        self.corpus.mark_done(entry)
        self._completed += 1

        self.query_one(f"#todo-{id(entry)}", ListItem).remove()
        self.todos.pop(idx)

        self.query_one("#todo-quote", Label).update(
            f"[{C_GREEN}]{get_quote()}[/{C_GREEN}]"
        )

        if not self.todos:
            self.set_timer(1.8, lambda: self.dismiss(self._completed))


# ── Main App ──────────────────────────────────────────────────────────────────

class TampNoteApp(App):
    """
    tamp-note TUI. Owns layout, routes input, delegates to command handlers.
    """

    CSS = CSS

    BINDINGS = [
        Binding("ctrl+d", "quit",       show=False),
        Binding("ctrl+r", "focus_find", show=False),
    ]

    def __init__(self, config: Config, corpus: Corpus) -> None:
        super().__init__()
        self.config  = config
        self.corpus  = corpus

        self._history:       list[str] = []
        self._hist_idx:      int       = -1
        self._draft:         str       = ""
        self._palette_open:  bool      = False
        self._taghints_open: bool      = False

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Vertical(id="root"):
            yield WelcomePanel(self.config, self.corpus)
            with Container(id="output-wrap"):
                yield RichLog(id="log", highlight=True, markup=True)
            with Horizontal(id="input-bar"):
                yield Label("> ", id="prompt")
                yield NoteInput(placeholder="type a note, or /command", id="input")
            yield HelpPanel()
            yield CommandPalette()
            yield TagHints()
            yield Label(
                f"[{C_BORDER}]?[/{C_BORDER}] help   "
                f"[{C_BORDER}]/[/{C_BORDER}] commands   "
                f"[{C_BORDER}]ctrl+d[/{C_BORDER}] quit   "
                f"[{C_DIM}]add +todo to any entry to create a todo[/{C_DIM}]",
                id="hint-bar",
            )
            with Horizontal(id="status-bar"):
                yield Label("", id="status-left")
                yield Label("", id="status-right")

    def on_mount(self) -> None:
        self.query_one("#input", NoteInput).focus()
        self._refresh_welcome_stats()
        self._refresh_status()

    # ── Key routing: ? and q from NoteInput ───────────────────────────────────

    def on_note_input_special_key(self, message: NoteInput.SpecialKey) -> None:
        if message.key == "?":
            self._toggle_help()
        elif message.key == "q":
            self.exit()

    # ── Key routing: text changing in the input field ─────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        value = event.value

        # Any typing closes the help panel
        if self.query_one(HelpPanel).is_open:
            self.query_one(HelpPanel).close()

        # Show palette while typing /word (close once a space appears — user is typing args)
        if value.startswith("/") and " " not in value:
            self.query_one(CommandPalette).filter(value[1:])
            self.query_one(CommandPalette).open()
            self._palette_open = True
            self._close_taghints()
            return

        if self._palette_open:
            self._close_palette(clear_input=False)

        # Show tag hints when the last word starts with @ or + followed by text
        last_word = value.split()[-1] if value.split() else ""
        if last_word and last_word[0] in ("@", "+") and len(last_word) > 1:
            prefix  = last_word[0]
            partial = last_word[1:].lower()
            matches = sorted(
                tag for tag in self.corpus.tag_counts()
                if tag.startswith(prefix) and tag[1:].startswith(partial)
            )
            if matches:
                self.query_one(TagHints).load(matches)
                self.query_one(TagHints).open()
                self._taghints_open = True
                return

        if self._taghints_open:
            self._close_taghints()

    # ── Key routing: Enter pressed ────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw   = event.value.strip()
        field = self.query_one("#input", NoteInput)
        field.value = ""

        self._hist_idx = -1
        self._draft    = ""
        self.query_one(HelpPanel).close()
        self._close_palette(clear_input=False)
        self._close_taghints()

        if not raw:
            return

        if not self._history or self._history[0] != raw:
            self._history.insert(0, raw)
        if len(self._history) > 200:
            self._history.pop()

        if raw.startswith("/"):
            self._run_command(raw)
        else:
            self._add_entry(raw)

    # ── Key routing: everything else ──────────────────────────────────────────

    def on_key(self, event) -> None:
        field   = self.query_one("#input", NoteInput)
        palette = self.query_one(CommandPalette)
        hints   = self.query_one(TagHints)
        help_p  = self.query_one(HelpPanel)

        # Escape closes help panel if open
        if event.key == "escape" and help_p.is_open:
            help_p.close()
            event.prevent_default()
            return

        # ── Palette navigation ────────────────────────────────────────────────
        if self._palette_open:
            if event.key == "down":
                palette.move_cursor(1);  event.prevent_default(); return
            if event.key == "up":
                palette.move_cursor(-1); event.prevent_default(); return
            if event.key in ("enter", "tab"):
                name = palette.selected_command()
                if name:
                    self._close_palette(clear_input=True)
                    if REGISTRY[name].has_args:
                        field.value = f"/{name} "
                        field.cursor_position = len(field.value)
                    else:
                        self._run_command(f"/{name}")
                event.prevent_default()
                return
            if event.key == "escape":
                self._close_palette(clear_input=True)
                event.prevent_default()
                return

        # ── Tag hint navigation ───────────────────────────────────────────────
        if self._taghints_open:
            if event.key == "down":
                hints.move_cursor(1);  event.prevent_default(); return
            if event.key == "up":
                hints.move_cursor(-1); event.prevent_default(); return
            if event.key in ("tab", "enter"):
                tag = hints.selected_tag()
                if tag:
                    words       = field.value.split()
                    words[-1]   = tag
                    field.value = " ".join(words) + " "
                    field.cursor_position = len(field.value)
                self._close_taghints()
                event.prevent_default()
                return
            if event.key == "escape":
                self._close_taghints()
                event.prevent_default()
                return

        # ── Command history ───────────────────────────────────────────────────
        if event.key == "up":
            if not self._history:
                return
            if self._hist_idx == -1:
                self._draft = field.value
            self._hist_idx = min(self._hist_idx + 1, len(self._history) - 1)
            field.value = self._history[self._hist_idx]
            field.cursor_position = len(field.value)
            event.prevent_default()
            return

        if event.key == "down":
            if self._hist_idx == -1:
                return
            self._hist_idx -= 1
            field.value   = self._draft if self._hist_idx == -1 else self._history[self._hist_idx]
            field.cursor_position = len(field.value)
            event.prevent_default()
            return

    # ── Core actions ──────────────────────────────────────────────────────────

    def _add_entry(self, text: str) -> None:
        entry = self.corpus.append_entry(text)
        self.query_one("#log", RichLog).write(
            f"[{C_MID}]{entry.time}[/{C_MID}]  {entry.text}"
        )
        self._refresh_welcome_stats()
        self._refresh_status(f"added · {date.today().isoformat()}")

    def _run_command(self, raw: str) -> None:
        log = self.query_one("#log", RichLog)

        try:
            result = dispatch(self.corpus, raw)
        except Exception as exc:
            log.write(f"[{C_RED}]error in {raw!r}: {exc}[/{C_RED}]")
            return

        log.write(f"[{C_RED}]{raw}[/{C_RED}]")

        if result.kind == "todo_list":
            todos = result.data or []
            if todos:
                def on_todo_close(n: int) -> None:
                    if n > 0:
                        self._refresh_welcome_stats()
                        self._refresh_status(f"{n} done")
                self.push_screen(TodoScreen(self.corpus, todos), on_todo_close)
            else:
                log.write(f"[{C_GREEN}]no open todos. clean slate.[/{C_GREEN}]")
            return

        if result.output:
            colour = {
                "success": C_GREEN,
                "error":   C_RED,
                "info":    C_GREY,
                "table":   C_TEXT,
            }.get(result.kind, C_TEXT)
            log.write(f"[{colour}]{result.output}[/{colour}]")

        if result.action.startswith("open_editor:"):
            self._open_in_editor(result.action.removeprefix("open_editor:"))
        elif result.action == "exit":
            self.exit()

        self._refresh_status()

    def _toggle_help(self) -> None:
        """Show or hide the help panel. Close other panels first."""
        help_p = self.query_one(HelpPanel)
        if help_p.is_open:
            help_p.close()
        else:
            self._close_palette(clear_input=False)
            self._close_taghints()
            help_p.open()

    def _open_in_editor(self, path: str) -> None:
        with self.suspend():
            subprocess.run([self.config.resolve_editor(), path])
            os.system("stty sane 2>/dev/null || true")
        self.refresh(layout=True)

    # ── Overlay helpers ───────────────────────────────────────────────────────

    def _close_palette(self, clear_input: bool) -> None:
        self.query_one(CommandPalette).close()
        self._palette_open = False
        if clear_input:
            self.query_one("#input", NoteInput).value = ""

    def _close_taghints(self) -> None:
        self.query_one(TagHints).close()
        self._taghints_open = False

    # ── UI refresh ────────────────────────────────────────────────────────────

    def _refresh_welcome_stats(self) -> None:
        today  = self.corpus.today()
        n_logs = len(self.corpus.all_logs())
        try:
            self.query_one("#stat-label", Label).update(
                f"[{C_BORDER}]{n_logs} logs · {len(today.entries)} today[/{C_BORDER}]"
            )
        except Exception:
            pass

    def _refresh_status(self, message: str = "") -> None:
        todos = self.corpus.open_todos()
        self.query_one("#status-left", Label).update(
            f"[{C_MID}]{message}[/{C_MID}]" if message else ""
        )
        self.query_one("#status-right", Label).update(
            f"[{C_AMBER}]{len(todos)} open[/{C_AMBER}]" if todos else ""
        )

    # ── Textual actions ───────────────────────────────────────────────────────

    def action_quit(self) -> None:
        self.exit()

    def action_focus_find(self) -> None:
        field = self.query_one("#input", NoteInput)
        field.value = "/find "
        field.cursor_position = len(field.value)
