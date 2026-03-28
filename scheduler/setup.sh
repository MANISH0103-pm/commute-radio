#!/bin/bash
# ── Commute Radio · Scheduler Setup ─────────────────────────────────────────
# Run this once to install the 3PM daily trigger.
# You can safely run it again — it unloads first to avoid duplicates.

PLIST_SRC="$(dirname "$0")/com.commute-radio.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.commute-radio.plist"

echo "Commute Radio — Scheduler Setup"
echo "================================"

# Copy plist to the correct macOS location
cp "$PLIST_SRC" "$PLIST_DEST"
echo "✓ Copied plist to $PLIST_DEST"

# Unload first (in case it's already loaded) then reload
launchctl unload "$PLIST_DEST" 2>/dev/null
launchctl load "$PLIST_DEST"
echo "✓ Scheduler activated — will run daily at 3:00 PM"

echo ""
echo "Useful commands:"
echo "  View logs:       cat /tmp/commute-radio.log"
echo "  Run now:         launchctl start com.commute-radio"
echo "  Stop automation: launchctl unload ~/Library/LaunchAgents/com.commute-radio.plist"
echo "  Run manually:    cd ~/commute-radio && uv run python run.py"
