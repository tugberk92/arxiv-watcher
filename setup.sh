#!/usr/bin/env bash
#
# One-command setup for arxiv-watcher.
#   ./setup.sh            # install everything, run once, schedule at 09:30
#   ./setup.sh 08:00      # ...schedule at a different time
#
# It will:
#   1. find a Python 3 (override with: PYTHON=/path/to/python ./setup.sh)
#   2. install terminal-notifier (clickable notifications) if Homebrew is present
#   3. install + load the daily LaunchAgent (auto mode, low-volume, no rate-limiting)
#   4. create double-clickable digest launchers in ./launchers/
#   5. run once so you see it working
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEDULE="${1:-09:30}"
PY="${PYTHON:-$(command -v python3 || true)}"
OUT="$HOME/Papers/arxiv_hits"

if [[ -z "$PY" ]]; then
  echo "✖ No python3 found. Install Python 3, or run: PYTHON=/path/to/python3 ./setup.sh"
  exit 1
fi
echo "• Python:   $PY"
echo "• Schedule: daily $SCHEDULE  (+ cheap hourly catch-up checks)"

# 1) Clickable notifications -------------------------------------------------
if ! command -v terminal-notifier >/dev/null 2>&1 \
   && [[ ! -x /opt/homebrew/bin/terminal-notifier ]] \
   && [[ ! -x /usr/local/bin/terminal-notifier ]]; then
  if command -v brew >/dev/null 2>&1; then
    echo "• Installing terminal-notifier (so clicking a notification opens arXiv)…"
    brew install terminal-notifier
  else
    echo "⚠️  Homebrew not found — notifications will still work, but clicking one"
    echo "    opens Script Editor instead of arXiv. To fix: install https://brew.sh"
    echo "    then run:  brew install terminal-notifier"
  fi
else
  echo "• terminal-notifier already installed ✓"
fi

# 2) Install + load the daily LaunchAgent ------------------------------------
echo "• Installing the daily scheduler…"
"$PY" "$HERE/arxiv_watcher.py" \
  --build-plist --install-plist \
  --schedule "$SCHEDULE" \
  --plist-every-hours 20 \
  --out "$OUT"

# 3) Double-clickable digest launchers ---------------------------------------
LAUNCHERS="$HERE/launchers"
mkdir -p "$LAUNCHERS"
make_launcher () {  # $1 = filename, $2 = window args (written literally)
  local file="$LAUNCHERS/$1"
  {
    echo '#!/usr/bin/env bash'
    echo "exec \"$PY\" \"$HERE/arxiv_watcher.py\" $2 --no-dedupe --dry --open"
  } > "$file"
  chmod +x "$file"
}
make_launcher "Digest - last 30 days.command" "--days 30"
make_launcher "Digest - this year.command"    "--year \$(date +%Y)"
echo "• Created double-click launchers in: $LAUNCHERS"

# 4) Run once so you see results now -----------------------------------------
echo "• Running once now…"
launchctl kickstart -k "gui/$(id -u)/com.arxiv.watcher" || true

cat <<EOF

✅ Done.
   • Daily notifications: automatic, click one to open the arXiv page.
   • On-demand list:  double-click a file in launchers/, or run e.g.
        $PY $HERE/arxiv_watcher.py --days 30 --no-dedupe --dry --open
        $PY $HERE/arxiv_watcher.py --year 2026 --no-dedupe --dry --open
        $PY $HERE/arxiv_watcher.py --since 2026-01-01 --until 2026-03-31 --no-dedupe --dry --open
   • Tune what you track by editing the files in patterns/.
EOF
