# OPERATIONS_RUNBOOK.md

## 1. Normal state check

```bash
systemctl status bili-live-keeper.service --no-pager
systemctl status bili-songbot-stream-sync.path --no-pager
systemctl status bili-songbot.service --no-pager
systemctl status bili-live-keeper-push.service --no-pager || true
ss -antp | grep -E "1935|ffmpeg|live-push" || true
curl -fsS http://127.0.0.1:8787/healthz || true
```

## 2. Normal logs

```bash
journalctl -u bili-live-keeper.service -n 120 --no-pager
journalctl -u bili-songbot-stream-sync.service -n 120 --no-pager
tail -200 /srv/bili-songbot/logs/systemd.log
```

## 3. Manually check Bilibili live state

```bash
cd /opt/bili-live-keeper
sudo -u bili-live-keeper env -u DISPLAY -u XAUTHORITY \
  HOME=/var/lib/bili-live-keeper \
  XDG_CACHE_HOME=/var/lib/bili-live-keeper/.cache \
  /opt/bili-live-keeper/.venv/bin/python -m bili_live_keeper.cli check
```

## 4. Manually start live room and refresh stream.env

Only run when the room is offline or a new key is needed.

```bash
cd /opt/bili-live-keeper
sudo -u bili-live-keeper env -u DISPLAY -u XAUTHORITY \
  HOME=/var/lib/bili-live-keeper \
  XDG_CACHE_HOME=/var/lib/bili-live-keeper/.cache \
  /opt/bili-live-keeper/.venv/bin/python -m bili_live_keeper.cli start-once
```

Check masked stream env:

```bash
sed -E 's/(key=)[^&"]+/\1***MASKED***/g; s/(streamname=)[^&"]+/\1***MASKED***/g' \
  /opt/bili-live-keeper/runtime/stream.env
```

## 5. Manually apply stream.env to songbot

```bash
systemctl start bili-songbot-stream-sync.service
sleep 10
systemctl status bili-songbot.service --no-pager
ss -antp | grep -E "1935|ffmpeg|live-push" || true
```

## 6. If songbot is down

Do not blindly restart with a stale key. First check whether keeper has a fresh `stream.env`.

```bash
ls -lh /opt/bili-live-keeper/runtime/stream.env
journalctl -u bili-live-keeper.service -n 120 --no-pager
journalctl -u bili-songbot-stream-sync.service -n 120 --no-pager
```

If `stream.env` is fresh, trigger sync:

```bash
systemctl start bili-songbot-stream-sync.service
```

## 7. If keeper is down

```bash
systemctl status bili-live-keeper.service --no-pager
journalctl -u bili-live-keeper.service -n 200 --no-pager
```

Try restart:

```bash
systemctl restart bili-live-keeper.service
```

If cookies expired, rerun login:

```bash
sudo BILIUP_BIN=/opt/bili-live-keeper/bin/biliup /opt/bili-live-keeper/scripts/login_biliup.sh
systemctl restart bili-live-keeper.service
```

## 8. If Bilibili asks for verification

Do not attempt to bypass verification. The user must complete login/verification manually. After verification, refresh cookies and restart keeper.

## 9. Do not enable black-screen keeper pusher

```bash
systemctl disable --now bili-live-keeper-push.service || true
systemctl mask bili-live-keeper-push.service || true
```

## 10. Stop everything safely

Only when explicitly requested:

```bash
systemctl stop bili-live-keeper.service || true
systemctl stop bili-songbot.service || true
pkill -f "python -m bili_songbot" || true
pkill -f "ffmpeg.*live.ts.fifo" || true
rm -f /srv/bili-songbot/runtime/live.ts.fifo
```
