#!/usr/bin/env bash
set -euo pipefail

echo "==== time ===="
date

echo
echo "==== keeper ===="
systemctl status bili-live-keeper.service --no-pager || true
journalctl -u bili-live-keeper.service -n 120 --no-pager || true

echo
echo "==== stream sync ===="
systemctl status bili-songbot-stream-sync.path --no-pager || true
journalctl -u bili-songbot-stream-sync.service -n 120 --no-pager || true

echo
echo "==== songbot ===="
systemctl status bili-songbot.service --no-pager || true

echo
echo "==== rtmp connection ===="
ss -antp | grep -E "1935|ffmpeg|live-push" || true

echo
echo "==== songbot recent key errors ===="
if [[ -f /srv/bili-songbot/logs/systemd.log ]]; then
  grep -Ei "RTMP_BROKEN_PIPE_FATAL|Broken pipe|End of file|Conversion failed|Traceback|Exception|ERROR|CRITICAL|启动推流|开始播放"     /srv/bili-songbot/logs/systemd.log     | sed -E 's/(key=)[^&"]+/***MASKED***/g; s/(streamname=)[^&"]+/***MASKED***/g'     | tail -150 || true
else
  echo "/srv/bili-songbot/logs/systemd.log not found"
fi

echo
echo "==== keeper env ===="
if [[ -f /opt/bili-live-keeper/.env ]]; then
  grep -E '^(BILI_ROOM_ID|BILIUP_COOKIE_FILE|HEADLESS|DRY_RUN|LIVE_AREA_PARENT|LIVE_AREA_CHILD|PUSH_KEEPALIVE_ENABLED|RUNTIME_STREAM_ENV|CHECK_INTERVAL_SECONDS|STOP_CONFIRM_TIMES|START_COOLDOWN_SECONDS)='     /opt/bili-live-keeper/.env || true
else
  echo "/opt/bili-live-keeper/.env not found"
fi

echo
echo "==== stream env masked ===="
if [[ -f /opt/bili-live-keeper/runtime/stream.env ]]; then
  ls -lh /opt/bili-live-keeper/runtime/stream.env
  sed -E 's/(key=)[^&"]+/***MASKED***/g; s/(streamname=)[^&"]+/***MASKED***/g'     /opt/bili-live-keeper/runtime/stream.env
else
  echo "stream.env not found"
fi
