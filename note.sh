#!/usr/bin/env bash
# tamp-note — minimal CLI note taking, part of the tamp toolkit
# https://github.com/tamp/tamp-note
#
# Usage:
#   tamp-note "your idea"    Append a timestamped note to today's log
#   tamp-note                Open today's log in $EDITOR
#   tamp-note open [topic]   Open/create a thematic note (e.g. tamp-note open fonts)
#   tamp-note find <query>   Search across all notes (case-insensitive)
#   tamp-note todo           List all +todo items with source file and line
#   tamp-note done <pattern> Mark matching +todo as done (strikethrough ~~text~~)
#   tamp-note last [n]       Show last n entries with source date (default: 10)
#   tamp-note tags           List all @context and +action tags in use with counts
#   tamp-note help           Show usage
#
# Tip: alias note='tamp-note' for a smoother daily experience.

set -euo pipefail

NOTES_DIR="${NOTES_DIR:-$HOME/Notes}"
mkdir -p "$NOTES_DIR"

TODAY="$NOTES_DIR/$(date +%Y-%m-%d).md"

# ─── colors (Lunar Lobby palette) ─────────────────────────────────────────────
GOLD='\033[33m'       # #D4A853 — headers, labels
GREEN='\033[32m'      # #ACBF96 — success
TEAL='\033[36m'       # #72B4B0 — file paths, accents
DIM='\033[90m'        # #706C68 — muted text
RED='\033[31m'        # #C87A72 — errors
AMBER='\033[93m'      # #BB8B62 — +todo highlights
RESET='\033[0m'

# ─── helpers ──────────────────────────────────────────────────────────────────

_usage() {
  printf "${GOLD}tamp-note${RESET} — minimal CLI note taking\n\n"
  printf "  ${TEAL}tamp-note${RESET} \"your idea\"      Append a timestamped note to today's log\n"
  printf "  ${TEAL}tamp-note${RESET}                  Open today's log in \$EDITOR\n"
  printf "  ${TEAL}tamp-note open${RESET} [topic]     Open/create a thematic note\n"
  printf "  ${TEAL}tamp-note find${RESET} <query>     Search all notes (case-insensitive)\n"
  printf "  ${TEAL}tamp-note todo${RESET}             List all +todo items with source file\n"
  printf "  ${TEAL}tamp-note done${RESET} <pattern>   Mark matching +todo as done\n"
  printf "  ${TEAL}tamp-note last${RESET} [n]         Show last n entries with date (default: 10)\n"
  printf "  ${TEAL}tamp-note tags${RESET}             List all @context and +action tags with counts\n"
  printf "  ${TEAL}tamp-note help${RESET}             Show this message\n"
  printf "\n"
  printf "${DIM}Tags:${RESET}\n"
  printf "  ${DIM}@context${RESET}   e.g. @dev, @design, @music\n"
  printf "  ${DIM}+action${RESET}    e.g. +todo, +read, +idea\n"
  printf "\n"
  printf "${DIM}Environment:${RESET}\n"
  printf "  ${DIM}NOTES_DIR${RESET}  Override notes location (default: ~/Notes)\n"
  printf "  ${DIM}EDITOR${RESET}     Editor used by open command (default: vim)\n"
  printf "\n"
  printf "${DIM}Tip: alias note='tamp-note' for faster daily use.${RESET}\n"
}

_append() {
  local text="$*"
  local timestamp
  timestamp=$(date +%H:%M)

  if [[ ! -s "$TODAY" ]]; then
    printf "# %s\n\n" "$(date '+%A, %B %-d %Y')" >> "$TODAY"
  fi

  printf -- "- %s %s\n" "$timestamp" "$text" >> "$TODAY"
  printf "${GREEN}✔${RESET}  ${DIM}%s${RESET}  %s  %s\n" "$(basename "$TODAY")" "$timestamp" "$text"
}

_open() {
  local topic="${1:-}"
  if [[ -z "$topic" ]]; then
    if [[ ! -s "$TODAY" ]]; then
      printf "# %s\n\n" "$(date '+%A, %B %-d %Y')" >> "$TODAY"
    fi
    ${EDITOR:-vim} "$TODAY"
  else
    ${EDITOR:-vim} "$NOTES_DIR/${topic}.md"
  fi
}

_find() {
  local query="${1:-}"
  if [[ -z "$query" ]]; then
    printf "${RED}error:${RESET} usage: tamp-note find <query>\n" >&2
    exit 1
  fi

  local results
  results=$(grep -rn --include="*.md" -i "$query" "$NOTES_DIR" 2>/dev/null \
    | sed "s|${NOTES_DIR}/||" || true)

  if [[ -z "$results" ]]; then
    printf "${DIM}no results for:${RESET} %s\n" "$query"
    return
  fi

  printf "${GOLD}--- results: %s ---${RESET}\n" "$query"
  echo "$results" | while IFS=: read -r file line content; do
    printf "  ${TEAL}%-28s${RESET}  ${DIM}:%s${RESET}  %s\n" "$file" "$line" "$content"
  done
}

_todo() {
  local results
  results=$(grep -rn --include="*.md" "+todo" "$NOTES_DIR" 2>/dev/null \
    | grep -v "~~" \
    | sed "s|${NOTES_DIR}/||" || true)

  if [[ -z "$results" ]]; then
    printf "${DIM}no +todo items found${RESET}\n"
    return
  fi

  printf "${GOLD}--- +todo ---${RESET}\n"
  echo "$results" | while IFS=: read -r file line content; do
    printf "  ${TEAL}%-28s${RESET}  ${DIM}:%s${RESET}  ${AMBER}%s${RESET}\n" "$file" "$line" "$content"
  done
}

_done() {
  local pattern="${1:-}"
  if [[ -z "$pattern" ]]; then
    printf "${RED}error:${RESET} usage: tamp-note done <pattern>\n" >&2
    exit 1
  fi

  local matched=0
  while IFS= read -r filepath; do
    local file="$NOTES_DIR/$filepath"
    if grep -q "$pattern" "$file" 2>/dev/null; then
      # Wrap matched line content in ~~ for markdown strikethrough
      sed -i.bak "/$pattern/s/- \([0-9][0-9]:[0-9][0-9] .*\)/- ~~\1~~/" "$file" \
        && rm -f "${file}.bak"
      printf "${GREEN}✔${RESET}  marked done in ${TEAL}%s${RESET}\n" "$filepath"
      matched=1
    fi
  done < <(ls "$NOTES_DIR"/*.md 2>/dev/null | sed "s|${NOTES_DIR}/||")

  if [[ $matched -eq 0 ]]; then
    printf "${DIM}no matching +todo found for:${RESET} %s\n" "$pattern"
  fi
}

_last() {
  local n="${1:-10}"
  local dated_files
  dated_files=$(ls -t "$NOTES_DIR"/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md 2>/dev/null | head -7)

  if [[ -z "$dated_files" ]]; then
    printf "${DIM}no daily notes found in %s${RESET}\n" "$NOTES_DIR"
    return
  fi

  printf "${GOLD}--- last %s entries ---${RESET}\n" "$n"

  # Collect entries with source date prefix
  local entries=""
  for f in $dated_files; do
    local date_label
    date_label=$(basename "$f" .md)
    while IFS= read -r line; do
      entries="${entries}${date_label}  ${line}\n"
    done < <(grep "^- " "$f" 2>/dev/null || true)
  done

  if [[ -z "$entries" ]]; then
    printf "${DIM}no entries found${RESET}\n"
    return
  fi

  printf "%b" "$entries" | tail -n "$n" | while IFS= read -r entry; do
    local date_part content_part
    date_part=$(echo "$entry" | cut -c1-10)
    content_part=$(echo "$entry" | cut -c13-)
    printf "  ${TEAL}%s${RESET}  %s\n" "$date_part" "$content_part"
  done
}

_tags() {
  printf "${GOLD}--- tags in use ---${RESET}\n"

  # @context tags
  printf "\n${DIM}@context${RESET}\n"
  grep -rh --include="*.md" -o "@[a-zA-Z][a-zA-Z0-9_-]*" "$NOTES_DIR" 2>/dev/null \
    | sort | uniq -c | sort -rn \
    | while read -r count tag; do
        printf "  ${TEAL}%-20s${RESET}  ${DIM}%s${RESET}\n" "$tag" "$count"
      done || printf "  ${DIM}none found${RESET}\n"

  # +action tags
  printf "\n${DIM}+action${RESET}\n"
  grep -rh --include="*.md" -o "+[a-zA-Z][a-zA-Z0-9_-]*" "$NOTES_DIR" 2>/dev/null \
    | sort | uniq -c | sort -rn \
    | while read -r count tag; do
        printf "  ${AMBER}%-20s${RESET}  ${DIM}%s${RESET}\n" "$tag" "$count"
      done || printf "  ${DIM}none found${RESET}\n"
}

# ─── dispatch ─────────────────────────────────────────────────────────────────

case "${1:-}" in
  "")             _open ;;
  help|--help|-h) _usage ;;
  open)           shift; _open "${1:-}" ;;
  find)           shift; _find "${*:-}" ;;
  todo)           _todo ;;
  done)           shift; _done "${*:-}" ;;
  last)           _last "${2:-10}" ;;
  tags)           _tags ;;
  *)              _append "$@" ;;
esac
