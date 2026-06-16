#!/usr/bin/env bash
set -euo pipefail

cd /srv/bili-songbot

echo "==== time ===="
date

echo
echo "==== systemd status ===="
systemctl status bili-songbot --no-pager || true

echo
echo "==== systemd restart info ===="
systemctl show bili-songbot -p NRestarts -p ActiveState -p SubState -p ExecMainStatus || true

echo
echo "==== processes ===="
ps aux | grep -E "python -m bili_songbot|bili_songbot|ffmpeg" | grep -v grep || true

echo
echo "==== rtmp connection ===="
ss -antp | grep -E "1935|ffmpeg|live-push" || true

echo
echo "==== last systemd journal ===="
journalctl -u bili-songbot -n 80 --no-pager || true

echo
echo "==== key errors from app log ===="
if [ -f logs/systemd.log ]; then
  grep -Ei \
  "RTMP_BROKEN_PIPE_FATAL|Broken pipe|End of file|Connection reset|Connection refused|Conversion failed|Error submitting|Error writing|non-existing PPS|decode_slice_header|no frame|Output file is empty|No filtered frames|Traceback|Exception|ERROR|CRITICAL|FFmpeg 渲染失败|播放循环异常|启动推流|开始播放|转场" \
  logs/systemd.log | tail -200 || true
else
  echo "logs/systemd.log not found"
fi

echo
echo "==== dmesg kill/oom ===="
dmesg -T | grep -Ei "killed process|oom|out of memory|segfault|ffmpeg|python" | tail -80 || true

echo
echo "==== disk ===="
df -h

echo
echo "==== memory ===="
free -h
