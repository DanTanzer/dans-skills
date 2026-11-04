#!/usr/bin/env bash
# Checks that this Mac can export readable-diagrams pictures, and says what to do about anything missing.
#   bash doctor.sh   check only: changes nothing
# Exit 0 when every required check passes, 1 when something required is missing, 2 for an unknown option.
set -u

case "${1:-}" in
  "") ;;
  -h|--help) sed -n '2,4p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "doctor: unknown option '$1'. Run it with no option."; exit 2 ;;
esac

if [ -t 1 ]; then
  YES=$'\033[32m✓\033[0m'; NO=$'\033[31m✗\033[0m'; HMM=$'\033[33m!\033[0m'
else
  YES="✓"; NO="✗"; HMM="!"
fi
missing=0
warnings=0

line() { printf '  %s  %-12s %s\n' "$1" "$2" "$3"; }
todo() { printf '                  → %s\n' "$1"; }
fail() { line "$NO" "$1" "$2"; todo "$3"; missing=$((missing + 1)); }
warn() { line "$HMM" "$1" "$2"; todo "$3"; warnings=$((warnings + 1)); }
found_one() { for f in "$@"; do [ -e "$f" ] && return 0; done; return 1; }

echo "readable-diagrams doctor: can this Mac export pictures?"
echo

if command -v python3 >/dev/null 2>&1; then
  line "$YES" "Python" "$(python3 --version 2>&1)"
else
  fail "Python" "not found" "install Python 3, for example: brew install python"
fi

# rsvg-convert, from librsvg, draws each diagram's SVG as a PNG. Homebrew installs it.
if command -v rsvg-convert >/dev/null 2>&1; then
  line "$YES" "rsvg-convert" "$(rsvg-convert --version 2>/dev/null | head -n 1 | sed 's/^rsvg-convert version //')"
elif command -v brew >/dev/null 2>&1; then
  fail "rsvg-convert" "not found; it draws each SVG as a PNG" "brew install librsvg"
else
  fail "rsvg-convert" "not found; it draws each SVG as a PNG" "install Homebrew from https://brew.sh, then: brew install librsvg"
fi

if found_one /System/Library/Fonts/Supplemental/Arial.ttf /Library/Fonts/Arial.ttf "$HOME/Library/Fonts/Arial.ttf"; then
  line "$YES" "Arial" "found; the label widths are measured for it"
else
  warn "Arial" "not found; labels may run a little long" "install Arial, then look at each picture closely"
fi

if found_one /System/Library/Fonts/Menlo.ttc /Library/Fonts/Menlo.ttc "$HOME/Library/Fonts/Menlo.ttc"; then
  line "$YES" "Menlo" "found; file names use it"
else
  warn "Menlo" "not found; file names use another mono font" "nothing to fix: mono fonts share the same widths"
fi

echo
if [ "$missing" -eq 0 ] && [ "$warnings" -eq 0 ]; then
  echo "All set: this Mac can export pictures."
elif [ "$missing" -eq 0 ]; then
  echo "Ready, with $warnings warning(s) above."
else
  echo "$missing thing(s) to fix. Do each → line above, then run the doctor again."
fi
[ "$missing" -eq 0 ]
