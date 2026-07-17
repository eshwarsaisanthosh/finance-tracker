#!/bin/bash
# Daily finance-tracker refresh (run by launchd at 17:00).
# Rebuilds dashboard.html from live Plaid data and sends the sync alert.
# Each step is independent so one failure doesn't block the others.
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR" || exit 1

PY="$DIR/.venv/bin/python"
mkdir -p "$DIR/logs"
LOG="$DIR/logs/daily.log"

# ── EDIT THIS to see the dashboard on your phone ──────────────────────────
# Point it at a cloud folder that syncs to your phone, then the daily run
# drops dashboard.html there. Uncomment the ONE line for the app you use:
# DASHBOARD_DEST="$HOME/Library/Mobile Documents/com~apple~CloudDocs/finance"      # iCloud Drive
# DASHBOARD_DEST="$HOME/OneDrive/finance"                                          # OneDrive
# DASHBOARD_DEST="$HOME/Dropbox/finance"                                           # Dropbox
# DASHBOARD_DEST="$HOME/Library/CloudStorage/GoogleDrive-YOU@gmail.com/My Drive/finance"  # Google Drive
DASHBOARD_DEST="${DASHBOARD_DEST:-}"
# ──────────────────────────────────────────────────────────────────────────

echo "===== $(date '+%Y-%m-%d %H:%M:%S') daily run starting =====" >> "$LOG"

if [ ! -x "$PY" ]; then
  echo "ERROR: venv python not found at $PY" >> "$LOG"
  exit 1
fi

# 1. Rebuild the dashboard from the last ~100 days of live data.
"$PY" scripts/generate_dashboard.py >> "$LOG" 2>&1 \
  && echo "  dashboard OK" >> "$LOG" \
  || echo "  dashboard FAILED" >> "$LOG"

# 2. Send the incremental "new charges" alert via ntfy.
"$PY" -m src.main --sync >> "$LOG" 2>&1 \
  && echo "  sync/notify OK" >> "$LOG" \
  || echo "  sync/notify FAILED" >> "$LOG"

# 3. Copy the dashboard to the synced cloud folder set above (for phone access).
if [ -n "${DASHBOARD_DEST:-}" ] && [ -f "$DIR/dashboard.html" ]; then
  mkdir -p "$DASHBOARD_DEST"
  cp "$DIR/dashboard.html" "$DASHBOARD_DEST/dashboard.html" \
    && echo "  copied to $DASHBOARD_DEST" >> "$LOG" \
    || echo "  copy FAILED" >> "$LOG"
fi

echo "===== $(date '+%Y-%m-%d %H:%M:%S') daily run done =====" >> "$LOG"
