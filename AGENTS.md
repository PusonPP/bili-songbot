# AGENTS.md — Bilibili Songbot Codex Operating Instructions

_Last updated: 2026-06-16 14:55:42 UTC_

## 0. Scope and priority

This file is for Codex agents working in the project rooted at:

```text
/srv/bili-songbot
```

This is the primary workspace. Codex logs in as the Linux `root` account and may operate inside this project by default.

Codex may also inspect or modify the paired live-keeper project when necessary:

```text
/opt/bili-live-keeper
```

Only touch the live-keeper project when the task involves Bilibili live status detection, automatic live-room startup, RTMP key extraction, cookies, stream.env synchronization, or systemd service integration.

Do not modify unrelated projects or server-wide configuration unless the task explicitly requires it and the change is described before execution.

---

## 1. What this project does

`/srv/bili-songbot` is a 24/7 Bilibili live karaoke/song-request bot.

It is responsible for:

- Playing a prepared library of Zombieland Saga / Franchouchou-related songs and videos.
- Random playback when there is no request queue.
- Handling Bilibili danmaku song requests.
- Maintaining a queue with cooldowns and duplicate/invalid request handling.
- Rendering a live overlay UI showing current song, request hints, queue, and random preview.
- Feeding rendered MPEG-TS chunks into an FFmpeg pusher.
- Pushing the final live stream to Bilibili RTMP.
- Writing runtime and diagnostic logs under `/srv/bili-songbot`.

This project does not open the Bilibili live room by itself. It only pushes video/audio to the currently valid RTMP endpoint.

---

## 2. Paired live-keeper project

The paired project is:

```text
/opt/bili-live-keeper
```

It is responsible for:

- Checking whether the Bilibili room is currently live.
- Automatically opening the Bilibili live center dashboard with headless Chromium.
- Selecting/confirming the live area: `电台 / 聊天电台`.
- Clicking “start live” when the room is offline.
- Extracting the fresh RTMP server URL and stream key.
- Writing the new stream information to:

```text
/opt/bili-live-keeper/runtime/stream.env
```

The file `stream.env` is then consumed by the songbot bridge.

Do not enable or use any keeper black-screen/silent-audio pusher service. The real pusher is `bili-songbot`.

---

## 3. Current service topology

Expected final topology:

```text
bili-live-keeper.service
    -> detects Bilibili live status
    -> if offline, starts the live room
    -> writes /opt/bili-live-keeper/runtime/stream.env

bili-songbot-stream-sync.path
    -> watches /opt/bili-live-keeper/runtime/stream.env

bili-songbot-stream-sync.service
    -> runs /usr/local/sbin/bili-songbot-use-keeper-stream
    -> updates /srv/bili-songbot/config/.env
    -> restarts bili-songbot.service

bili-songbot.service
    -> renders and pushes the actual songbot stream to Bilibili RTMP
```

Expected service states during normal operation:

```text
bili-live-keeper.service          active/running
bili-songbot-stream-sync.path     active/waiting
bili-songbot.service              active/running
bili-live-keeper-push.service     masked or not found
RTMP connection                   ESTAB to :1935 from ffmpeg
```

Important design decision:

```text
bili-songbot.service is intentionally disabled but may be active/running.
```

It should not start on boot with an old RTMP key. It should be started by the stream-sync bridge after live-keeper obtains a fresh key.

---

## 4. Critical paths

Primary songbot project:

```text
/srv/bili-songbot
/srv/bili-songbot/config/.env
/srv/bili-songbot/runtime/
/srv/bili-songbot/logs/systemd.log
/srv/bili-songbot/scripts/
```

Live keeper:

```text
/opt/bili-live-keeper
/opt/bili-live-keeper/.env
/opt/bili-live-keeper/runtime/stream.env
/opt/bili-live-keeper/.venv/
/var/lib/bili-live-keeper
/var/lib/bili-live-keeper/biliup-cookies.json
/var/log/bili-live-keeper
```

Systemd units:

```text
/etc/systemd/system/bili-songbot.service
/etc/systemd/system/bili-live-keeper.service
/etc/systemd/system/bili-songbot-stream-sync.path
/etc/systemd/system/bili-songbot-stream-sync.service
```

Bridge script:

```text
/usr/local/sbin/bili-songbot-use-keeper-stream
```

---

## 5. Security rules

Never print, paste, commit, or expose:

- `RTMP_STREAM_KEY`
- `BILI_STREAM_KEY`
- `key=...`
- `streamname=...`
- `biliup-cookies.json`
- Bilibili cookies, SESSDATA, bili_jct, DedeUserID, tokens
- Full RTMP push URLs

When showing stream env or logs, mask secrets:

```bash
sed -E 's/(key=)[^&"]+/\1***MASKED***/g; s/(streamname=)[^&"]+/\1***MASKED***/g' /opt/bili-live-keeper/runtime/stream.env
```

If a key was exposed in logs, do not repost it. Recommend truncating logs after preserving necessary diagnostics:

```bash
truncate -s 0 /srv/bili-songbot/logs/systemd.log
chmod 600 /srv/bili-songbot/logs/systemd.log
chmod 600 /srv/bili-songbot/config/.env
chmod 600 /opt/bili-live-keeper/runtime/stream.env
chmod 600 /var/lib/bili-live-keeper/biliup-cookies.json
```

---

## 6. Operational guardrails

Before changing code or service files:

1. Read the relevant file.
2. Make a timestamped backup.
3. Change only the minimal required files.
4. Do not use `git add .`; add explicit paths only.
5. Run syntax checks.
6. Verify systemd units if edited.
7. Restart only the affected service.
8. Confirm with logs, process list, and RTMP connection.

Backup pattern:

```bash
cp path/to/file "path/to/file.bak.$(date +%F_%H%M%S)"
```

Systemd verify:

```bash
systemd-analyze verify /etc/systemd/system/bili-songbot.service
systemd-analyze verify /etc/systemd/system/bili-live-keeper.service
systemd-analyze verify /etc/systemd/system/bili-songbot-stream-sync.service /etc/systemd/system/bili-songbot-stream-sync.path
```

Python syntax check:

```bash
cd /srv/bili-songbot
source .venv/bin/activate
python3 -m py_compile $(find bili_songbot -name '*.py')
```

For live-keeper:

```bash
cd /opt/bili-live-keeper
/opt/bili-live-keeper/.venv/bin/python -m py_compile $(find src -name '*.py')
```

---

## 7. Normal health checks

Run from root:

```bash
systemctl status bili-live-keeper.service --no-pager
systemctl status bili-songbot-stream-sync.path --no-pager
systemctl status bili-songbot.service --no-pager
systemctl status bili-live-keeper-push.service --no-pager || true

journalctl -u bili-live-keeper.service -n 80 --no-pager
journalctl -u bili-songbot-stream-sync.service -n 80 --no-pager

ss -antp | grep -E "1935|ffmpeg|live-push" || true
curl -fsS http://127.0.0.1:8787/healthz || true
```

Expected:

```text
keeper heartbeat: live=true
songbot: active/running
ffmpeg RTMP connection: ESTAB
push service: masked/inactive/not found
```

---

## 8. Failure classification

### A. Songbot stopped, keeper says live=true

Check songbot logs and RTMP connection:

```bash
systemctl status bili-songbot.service --no-pager
tail -200 /srv/bili-songbot/logs/systemd.log
ss -antp | grep -E "1935|ffmpeg|live-push" || true
```

If `RTMP_BROKEN_PIPE_FATAL`, `Broken pipe`, or `End of file` appears, Bilibili likely closed the RTMP connection. Let keeper detect offline and start a new session; if necessary, run keeper start-once manually.

### B. Keeper stopped or failing

Check:

```bash
systemctl status bili-live-keeper.service --no-pager
journalctl -u bili-live-keeper.service -n 200 --no-pager
```

Common issues:

- Cookies expired.
- Bilibili asks for verification.
- Chromium/Playwright failure.
- Permission denied on `.env`, `runtime`, or cookie file.

### C. stream.env written but songbot did not restart

Check:

```bash
systemctl status bili-songbot-stream-sync.path --no-pager
journalctl -u bili-songbot-stream-sync.service -n 120 --no-pager
ls -lh /opt/bili-live-keeper/runtime/stream.env
```

Manual trigger:

```bash
systemctl start bili-songbot-stream-sync.service
```

### D. ffmpeg ESTAB but Bilibili page has no image

Check Bilibili dashboard first. If FFmpeg is connected and sending packets, this may be a platform/dashboard delay.

### E. `bili-live-keeper-push.service` exists or starts

Disable and mask it:

```bash
systemctl disable --now bili-live-keeper-push.service || true
systemctl mask bili-live-keeper-push.service || true
```

The black/silent keeper pusher must not compete with the songbot pusher.

---

## 9. Recovery commands

Manual keeper status check:

```bash
cd /opt/bili-live-keeper
sudo -u bili-live-keeper env -u DISPLAY -u XAUTHORITY \
  HOME=/var/lib/bili-live-keeper \
  XDG_CACHE_HOME=/var/lib/bili-live-keeper/.cache \
  /opt/bili-live-keeper/.venv/bin/python -m bili_live_keeper.cli check
```

Manual start live and generate stream.env:

```bash
cd /opt/bili-live-keeper
sudo -u bili-live-keeper env -u DISPLAY -u XAUTHORITY \
  HOME=/var/lib/bili-live-keeper \
  XDG_CACHE_HOME=/var/lib/bili-live-keeper/.cache \
  /opt/bili-live-keeper/.venv/bin/python -m bili_live_keeper.cli start-once
```

Manual sync to songbot:

```bash
systemctl start bili-songbot-stream-sync.service
```

Manual check after sync:

```bash
sleep 10
systemctl status bili-songbot.service --no-pager
ss -antp | grep -E "1935|ffmpeg|live-push" || true
```

---

## 10. Editing policy for Codex

Codex is allowed to:

- Inspect and edit `/srv/bili-songbot`.
- Inspect and edit `/opt/bili-live-keeper` only when required by live-status, auto-start, RTMP key, cookie, Chromium, or integration issues.
- Inspect and edit the related systemd units listed above.
- Create diagnostics under `/srv/bili-songbot/runtime/` and `/srv/bili-songbot/scripts/`.

Codex should avoid:

- Unrelated `/etc` edits.
- Reinstalling system packages unless necessary.
- Killing active streams unless the task explicitly requires recovery or restart.
- Enabling `bili-live-keeper-push.service`.
- Starting `bili-songbot.service` directly with stale keys unless this is part of a controlled manual recovery.
- Exposing secrets in output.

Before any potentially disruptive action, state the exact commands and expected effect.

---

## 11. Commit and changelog policy

If the project is a Git repository:

```bash
git status --short
```

Use explicit add paths only:

```bash
git add AGENTS.md README_CODEX.md docs/codex/OPERATION_LOG.md
```

Do not add runtime logs, `.env`, `stream.env`, cookies, media files, or temporary diagnostics unless explicitly requested.

Update:

```text
CHANGELOG_CODEX.md
docs/codex/OPERATION_LOG.md
```

for every meaningful Codex change.

---

## 12. Final answer format for Codex tasks

For each task, summarize:

- What was changed.
- Files touched.
- Commands run.
- Test results.
- Remaining risk.
- Whether any service was restarted.
- Whether secrets were redacted.
