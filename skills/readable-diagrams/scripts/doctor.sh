#!/usr/bin/env bash
# Checks that this Mac can export readable-diagrams pictures, and says what to do about anything missing.
#   bash doctor.sh             check only: changes nothing
#   bash doctor.sh --install   also install puppeteer next to these scripts, if Node cannot load it from here; no browser download
# Exit 0 when every required check passes, 1 when something required is missing, 2 for an unknown option.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHROME="${CHROME_PATH:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
NODE_MIN="14.14.0"
if [ "$PWD" = "$HERE" ]; then SELF="doctor.sh"; else SELF="$HERE/doctor.sh"; fi
case "$SELF" in *" "*) SELF="\"$SELF\"" ;; esac

# The export's own question, asked of Node from this folder: can it load puppeteer, and which copy? Node looks in
# node_modules here and in every folder above, so a puppeteer in the repo's own node_modules counts too. The probe
# prints the version and where it was found, or why not, and exits 1 when Node cannot load it.
IFS= read -r -d '' PROBE <<'JS'
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { dirname, join, sep } from 'node:path';
try {
  await import('puppeteer');
} catch (err) {
  const missing = err.code === 'ERR_MODULE_NOT_FOUND' && String(err.message).includes("'puppeteer'");
  console.log(missing ? 'Node cannot find it from the scripts folder' : 'found, but it does not load: ' + String(err.message).split('\n')[0]);
  process.exit(1);
}
try {
  const entry = createRequire(join(process.cwd(), 'probe.js')).resolve('puppeteer');
  const marker = sep + 'node_modules' + sep + 'puppeteer' + sep;
  const root = entry.slice(0, entry.lastIndexOf(marker) + marker.length - 1);
  const folder = dirname(root);
  const { version } = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
  console.log(version + (folder === join(process.cwd(), 'node_modules') ? ', next to the scripts' : ', in ' + folder));
} catch {
  console.log('loads');
}
JS
puppeteer_check() { (cd "$HERE" && node --input-type=module -e "$PROBE" 2>/dev/null); }

INSTALL=0
case "${1:-}" in
  "") ;;
  --install) INSTALL=1 ;;
  -h|--help) sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "doctor: unknown option '$1'. Use --install, or no option to check only."; exit 2 ;;
esac

if [ -t 1 ]; then
  YES=$'\033[32m✓\033[0m'; NO=$'\033[31m✗\033[0m'; HMM=$'\033[33m!\033[0m'
else
  YES="✓"; NO="✗"; HMM="!"
fi
missing=0
warnings=0

line() { printf '  %s  %-11s %s\n' "$1" "$2" "$3"; }
todo() { printf '                 → %s\n' "$1"; }
fail() { line "$NO" "$1" "$2"; todo "$3"; missing=$((missing + 1)); }
warn() { line "$HMM" "$1" "$2"; todo "$3"; warnings=$((warnings + 1)); }
at_least() { [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -n 1)" = "$2" ]; }  # is version $1 at least $2
found_one() { for f in "$@"; do [ -e "$f" ] && return 0; done; return 1; }

if [ "$INSTALL" = 1 ] && ! puppeteer_check >/dev/null; then
  if command -v npm >/dev/null 2>&1; then
    echo "Installing puppeteer next to the scripts, with no browser download..."
    if (cd "$HERE" && PUPPETEER_SKIP_DOWNLOAD=1 npm install --ignore-scripts --no-audit --no-fund >/dev/null 2>&1); then
      echo "Installed."
    else
      echo "npm install failed. Run it by hand to see why:"
      echo "  cd \"$HERE\" && PUPPETEER_SKIP_DOWNLOAD=1 npm install --ignore-scripts"
    fi
  else
    echo "npm was not found, so puppeteer cannot be installed yet."
  fi
  echo
fi

echo "readable-diagrams doctor: can this Mac export pictures?"
echo

if command -v python3 >/dev/null 2>&1; then
  line "$YES" "Python" "$(python3 --version 2>&1)"
else
  fail "Python" "not found" "install Python 3, for example: brew install python"
fi

if command -v node >/dev/null 2>&1; then
  v="$(node --version 2>/dev/null | sed 's/^v//')"
  if at_least "$v" "$NODE_MIN"; then
    line "$YES" "Node" "$v"
  else
    fail "Node" "$v is too old; puppeteer needs $NODE_MIN or newer" "update Node, for example: brew upgrade node"
  fi
else
  fail "Node" "not found" "install Node, for example: brew install node"
fi

if command -v npm >/dev/null 2>&1; then
  line "$YES" "npm" "$(npm --version 2>/dev/null)"
else
  fail "npm" "not found" "install Node again; npm comes with it"
fi

if [ -x "$CHROME" ]; then
  line "$YES" "Chrome" "$("$CHROME" --version 2>/dev/null | head -n 1 | sed 's/ *$//')"
else
  fail "Chrome" "not found at $CHROME" "install Google Chrome, or set CHROME_PATH to a Chrome or Chromium"
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

if ! command -v node >/dev/null 2>&1; then
  fail "puppeteer" "not checked: Node is missing" "install Node, then run: bash $SELF --install"
elif found="$(puppeteer_check)"; then
  line "$YES" "puppeteer" "$found"
else
  fail "puppeteer" "${found:-Node could not run the check}" "bash $SELF --install"
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
