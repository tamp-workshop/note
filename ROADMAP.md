# tamp — Roadmap

Where tamp is going and why. Items are marked by confidence level.
Nothing here is a promise. Small tools evolve slowly and deliberately.

---

## Now — active work

- [ ] `/todo` crashes with `ScreenError` when list is empty — fix is known
- [ ] `/todo` modal replaced with inline log rendering — more natural UX
- [ ] Welcome panel visual hierarchy — better contrast between name, date, stats
- [ ] Editor return artefact on some terminals
- [ ] `/last` groups entries by date with a visual separator

---

## Next — planned, design mostly settled

### tamp-task

A dedicated task manager reading the same `~/Notes/` corpus.

- CLI-first: `task list`, `task done <id>`, `task add "..."`
- Reads all `+todo` entries across all daily logs
- Adds `due:` and priority (Schema v2, backward compatible)
- Shares tamp-core entirely — no file parsing of its own
- Optional external sync (Things, Linear, GitHub Issues) as adapters

**Status:** Design document needed before implementation. See issue #6.

### Textual integration tests

- `App.run_test()` coverage for the TUI
- Priority flows: palette open/close, `?` toggle, inline `/todo`, tag autocomplete

---

## Later — planned, details still open

**tamp-insight** — weekly statistical digests. Entry counts, completion rates,
streaks, tag trends. Export to markdown. Local only.

**Schema v2** — optional stable `id:` field on entries for cross-tool
referencing. Backward compatible. Required before tamp-task can reliably
reference tamp-note entries.

---

## Speculative

**tamp-web** — local read-only web view. `tamp serve` → localhost.
Useful for browsing on mobile over a local network. Not a sync service.

**Multiple corpora** — config profiles for different `notes_dir` per project.
`tamp --profile work`.

---

## Out of scope

**Cloud sync** — use a synced folder (iCloud, Dropbox, git). tamp doesn't
need to know about it, and adding sync would compromise the plain-files guarantee.

**Rich text or attachments** — anything that can't be read with `cat` is out.

**Mobile app** — tamp-web covers the read-only mobile case.

---

## Version history

| Version | Date | Summary |
|---|---|---|
| v0.8.0 | March 2026 | Full rewrite — monorepo, tamp-core, Textual TUI |
| v0.1.x | 2025 | Original shell script, single file |
