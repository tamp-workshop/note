#!/usr/bin/env bash
# note — simple CLI note taking
# https://github.com/yourusername/note
#
# Usage:
#   note "your idea"         Append a timestamped note to today's log
#   note                     Open today's log in $EDITOR
#   note open [topic]        Open/create a thematic note (e.g. note open fonts)
#   note find <query>        Search across all notes
#   note todo                List all +todo items with source file and line
#   note last [n]            Show last n entries across recent logs (default: 10)
#   note help                Show usage

set -euo pipefail

NOTES_DIR="${NOTES_DIR:-$HOME/Notes}"
mkdir -p "$NOTES_DIR"

TODAY="$NOTES_DIR/$(date +%Y-%m-%d).md"

# ─── colours (TTY only) ────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_RESET='\033[0m'
  C_USER='\033[38;5;174m'    # terracotta  — prompt / checkmark
  C_PATH='\033[38;5;107m'    # sage-olive  — filenames
  C_ACCENT='\033[38;5;179m'  # warm amber  — section headers, tags
  C_MUTED='\033[38;5;103m'   # muted mauve — descriptions, counts
  C_DIM='\033[38;5;60m'      # dim         — line numbers, separators
else
  C_RESET='' C_USER='' C_PATH='' C_ACCENT='' C_MUTED='' C_DIM=''
fi

# ─── helpers ──────────────────────────────────────────────────────────────────

_usage() {
  printf "${C_ACCENT}note${C_RESET} — simple CLI note taking\n\n"
  printf "  ${C_PATH}%-24s${C_RESET} %s\n" \
    'note "your idea"'  "Append a timestamped note to today's log" \
    'note'              "Open today's log in \$EDITOR" \
    'note open [topic]' "Open/create a thematic note  (e.g. note open fonts)" \
    'note find'         "Show all tags in use (@context and +action)" \
    'note find <query>' "Search across all notes (case-insensitive)" \
    'note tags'         "Show all tags in use" \
    'note todo'         "List all open +todo items with source file" \
    'note done <query>' "Mark a matching +todo as done (struck through)" \
    'note last [n]'     "Show last n entries (default: 10)" \
    'note help'         "Show this message"
  printf "\n${C_MUTED}Tags:${C_RESET}\n"
  printf "  ${C_USER}%-22s${C_RESET} %s\n" \
    '@context' "e.g. @dev, @design, @music" \
    '+action'  "e.g. +todo, +read, +idea"
  printf "\n${C_MUTED}Environment:${C_RESET}\n"
  printf "  ${C_PATH}%-22s${C_RESET} %s\n" \
    'NOTES_DIR' "Override notes location (default: ~/Notes)" \
    'EDITOR'    "Editor for note open (default: vi)"
  printf "\n"
}

_append() {
  local text="$*"
  local timestamp
  timestamp=$(date +%H:%M)

  # Add a date header if the file is new or empty
  if [[ ! -s "$TODAY" ]]; then
    echo "# $(date '+%A, %B %-d %Y')" >> "$TODAY"
    echo "" >> "$TODAY"
  fi

  echo "- ${timestamp} ${text}" >> "$TODAY"
  printf "${C_USER}✔${C_RESET}  ${C_PATH}%s${C_RESET}  ${C_MUTED}%s${C_RESET}  %s\n" \
    "$(basename "$TODAY")" "$timestamp" "$text"
}

_open() {
  local topic="${1:-}"
  if [[ -z "$topic" ]]; then
    # Ensure today's file exists with a header before opening
    if [[ ! -s "$TODAY" ]]; then
      echo "# $(date '+%A, %B %-d %Y')" >> "$TODAY"
      echo "" >> "$TODAY"
    fi
    ${EDITOR:-vi} "$TODAY"
  else
    ${EDITOR:-vi} "$NOTES_DIR/${topic}.md"
  fi
}

_find() {
  local query="${1:-}"

  # No query → show tags overview as a discovery aid
  if [[ -z "$query" ]]; then
    _tags
    return
  fi

  local results
  results=$(grep -rn --include="*.md" -i "$query" "$NOTES_DIR" \
    | sed "s|${NOTES_DIR}/||" || true)

  if [[ -z "$results" ]]; then
    echo "no results for: $query"
    return
  fi

  printf '%s\n' "${C_MUTED}--- results: $query ---${C_RESET}"
  echo "$results" | while IFS=: read -r file line content; do
    printf "  ${C_PATH}%-28s${C_RESET}  ${C_DIM}:%-4s${C_RESET} %s\n" "$file" "$line" "$content"
  done
}

_todo() {
  local results
  # Exclude already-struck lines (~~...~~)
  results=$(grep -rn --include="*.md" '+todo' "$NOTES_DIR" 2>/dev/null \
    | grep -v '^\([^:]*\):[0-9]*:~~' \
    | sed "s|${NOTES_DIR}/||" || true)

  if [[ -z "$results" ]]; then
    echo "no open +todo items found."
    return
  fi

  printf '%s\n' "${C_ACCENT}--- +todo items ---${C_RESET}"
  echo "$results" | while IFS=: read -r file line content; do
    printf "  ${C_PATH}%-28s${C_RESET}  ${C_DIM}:%-4s${C_RESET} %s\n" "$file" "$line" "$content"
  done
}

_done() {
  local query="${1:-}"
  if [[ -z "$query" ]]; then
    echo "Usage: note done <query>" >&2
    exit 1
  fi

  local matched_file matched_line matched_content
  local match_count=0

  # Find open +todo lines matching query (not already struck through)
  while IFS=: read -r file line content; do
    matched_file="$file"
    matched_line="$line"
    matched_content="$content"
    (( match_count++ )) || true
  done < <(grep -rn --include="*.md" -i "$query" "$NOTES_DIR" 2>/dev/null \
    | grep '+todo' \
    | grep -v '~~' \
    | sed "s|${NOTES_DIR}/||")

  if [[ "$match_count" -eq 0 ]]; then
    echo "no open +todo matching: $query"
    return
  fi

  if [[ "$match_count" -gt 1 ]]; then
    echo "ambiguous — $match_count matches for: $query"
    echo "be more specific, or edit the file directly."
    return
  fi

  # Strip the leading '- HH:MM ' and wrap the rest in strikethrough
  local full_path="$NOTES_DIR/$matched_file"
  local struck

  # Turn '- 09:14 some text' into '~~09:14 some text~~'
  struck=$(echo "$matched_content" | sed 's/^- \([0-9][0-9]:[0-9][0-9] \)/~~\1/; s/$/~~/')

  # macOS-safe in-place sed using a temp file
  local tmp
  tmp=$(mktemp)
  awk -v line="$matched_line" -v replacement="$struck" \
    'NR==line {print replacement; next} {print}' \
    "$full_path" > "$tmp" && mv "$tmp" "$full_path"

  printf "${C_USER}✔${C_RESET}  marked done in ${C_PATH}%s${C_RESET}\n" "$matched_file"
}

_tags() {
  local actions contexts

  # Collect all +action tags (word after +, not just +todo)
  actions=$(grep -roh --include="*.md" '+[a-zA-Z][a-zA-Z0-9_-]*' "$NOTES_DIR" 2>/dev/null \
    | sed 's|.*:||' \
    | sort | uniq -c | sort -rn)

  # Collect all @context tags
  contexts=$(grep -roh --include="*.md" '@[a-zA-Z][a-zA-Z0-9_-]*' "$NOTES_DIR" 2>/dev/null \
    | sed 's|.*:||' \
    | sort | uniq -c | sort -rn)

  if [[ -z "$actions" && -z "$contexts" ]]; then
    echo "no tags found in $NOTES_DIR"
    return
  fi

  printf '%s\n' "${C_ACCENT}--- tags in use ---${C_RESET}"

  if [[ -n "$contexts" ]]; then
    printf "\n${C_USER}@context${C_RESET}\n"
    echo "$contexts" | while read -r count tag; do
      printf "  ${C_PATH}%-22s${C_RESET} ${C_MUTED}%s${C_RESET}\n" "$tag" "$count"
    done
  fi

  if [[ -n "$actions" ]]; then
    printf "\n${C_ACCENT}+action${C_RESET}\n"
    echo "$actions" | while read -r count tag; do
      printf "  ${C_PATH}%-22s${C_RESET} ${C_MUTED}%s${C_RESET}\n" "$tag" "$count"
    done
  fi
}

_last() {
  local n="${1:-10}"

  # Collect bullet lines from the most recent dated note files
  local dated_files
  dated_files=$(ls -t "$NOTES_DIR"/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md 2>/dev/null | head -7)

  if [[ -z "$dated_files" ]]; then
    echo "No daily notes found in $NOTES_DIR"
    return
  fi

  grep -h "^- " $dated_files 2>/dev/null | tail -n "$n" || echo "No entries found."
}

# ─── dispatch ─────────────────────────────────────────────────────────────────

case "${1:-}" in
  "")             _open ;;
  help|--help|-h) _usage ;;
  open)           shift; _open "${1:-}" ;;
  find)           shift; _find "${*:-}" ;;
  tags)           _tags ;;
  todo)           _todo ;;
  done)           shift; _done "${*:-}" ;;
  last)           _last "${2:-10}" ;;
  *)              _append "$@" ;;
esac
