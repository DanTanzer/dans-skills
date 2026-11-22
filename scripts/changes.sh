#!/bin/bash
# scripts/changes.sh <base>: the tests of the files this branch changed since it left <base>
# (committed, uncommitted and new files). The exit status is the result. The mol-repo-work formula runs it.
# A skill's tests live in skills/<skill>/scripts/tests. A changed test file runs; a changed script runs every test
# file that names it, or the skill's whole suite when none does. Shell files get bash -n, JSON files a parse.
set -u
cd "$(dirname "$0")/.." || exit 1
base="${1:?usage: scripts/changes.sh <base>}"
git rev-parse -q --verify "$base^{commit}" >/dev/null || base="origin/$base"
mb="$(git merge-base "$base" HEAD)" || { echo "changes: no merge base with $base"; exit 1; }
files="$( { git diff --name-only "$mb"; git ls-files --others --exclude-standard; } | sort -u)"
[ -n "$files" ] || { echo "no changes"; exit 0; }
PY=/opt/homebrew/bin/python3.14; [ -x "$PY" ] || PY=python3

status=0
fail() { echo "FAIL $*"; status=1; }
runs=""   # lines "<scripts folder> <test module or ALL>"
while IFS= read -r f; do
  [ -f "$f" ] || continue
  case "$f" in
    *.sh|.githooks/*) bash -n "$f" || fail "bash -n $f" ;;
    *.json) "$PY" -I -c 'import json,sys
try: json.load(open(sys.argv[1]))
except ValueError as e: sys.exit(str(e))' "$f" || fail "json $f" ;;
  esac
  [[ "$f" == skills/*/scripts/*.py ]] || continue
  dir="${f%%/scripts/*}/scripts"; rel="${f#"$dir"/}"
  if [[ "$rel" == tests/test_*.py ]]; then runs="$runs"$'\n'"$dir $(basename "$rel" .py)"; continue; fi
  stem="$(basename "$rel" .py)"
  hits="$(grep -lwE "$stem" "$dir"/tests/test_*.py 2>/dev/null)"
  if [ -n "$hits" ]; then for h in $hits; do runs="$runs"$'\n'"$dir $(basename "$h" .py)"; done
  else runs="$runs"$'\n'"$dir ALL"; fi
done <<<"$files"
for dir in $(printf '%s\n' "$runs" | awk 'NF {print $1}' | sort -u); do
  mods="$(printf '%s\n' "$runs" | awk -v d="$dir" '$1 == d {print $2}' | sort -u)"
  if grep -qx ALL <<<"$mods"; then args=(discover -s tests -t .); else args=($(sed 's/^/tests./' <<<"$mods")); fi
  out="$(cd "$dir" && "$PY" -m unittest "${args[@]}" 2>&1)" || fail "unittest in $dir"
  echo "$dir: ${args[*]}: $(grep -E '^(Ran|OK|FAILED)' <<<"$out" | paste -sd' ' -)"
  [ "$status" = 0 ] || grep -E '^(FAIL|ERROR):' <<<"$out"
done
[ -n "$runs" ] || echo "no skill script changed: static checks only"
echo "changes: exit $status"
exit $status
