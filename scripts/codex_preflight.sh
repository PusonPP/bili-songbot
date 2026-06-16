#!/usr/bin/env bash
set -euo pipefail

cd /srv/bili-songbot

echo "==== project ===="
pwd
find . -maxdepth 2 -type f | sort | head -200

echo
echo "==== git ===="
git status --short || true

echo
echo "==== python syntax ===="
if [[ -d .venv && -d bili_songbot ]]; then
  . .venv/bin/activate
  python3 -m py_compile $(find bili_songbot -name '*.py')
else
  echo "No .venv or bili_songbot package found; skipping py_compile."
fi

echo
echo "==== systemd verify ===="
systemd-analyze verify /etc/systemd/system/bili-songbot.service || true
systemd-analyze verify /etc/systemd/system/bili-live-keeper.service || true
systemd-analyze verify /etc/systemd/system/bili-songbot-stream-sync.service /etc/systemd/system/bili-songbot-stream-sync.path || true

echo
echo "==== service states ===="
systemctl status bili-live-keeper.service --no-pager || true
systemctl status bili-songbot-stream-sync.path --no-pager || true
systemctl status bili-songbot.service --no-pager || true
