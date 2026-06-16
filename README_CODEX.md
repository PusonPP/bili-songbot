# README_CODEX.md — Codex Handoff for `/srv/bili-songbot`

## Project identity

This repository is the Bilibili live song-request/karaoke project.

Primary directory:

```text
/srv/bili-songbot
```

Runtime role:

```text
Render song videos + overlay UI + danmaku request logic + queue logic + RTMP push to Bilibili
```

The project is paired with a second service:

```text
/opt/bili-live-keeper
```

Runtime role:

```text
Detect whether Bilibili live room is online; if offline, automatically open the live room and extract a fresh RTMP URL/key.
```

## Why there are two projects

The songbot only pushes media to RTMP. It cannot recover if Bilibili closes the live session and invalidates the stream key.

The live-keeper handles the Bilibili dashboard/session side:

1. Detect offline room.
2. Click start live.
3. Extract new RTMP info.
4. Write `/opt/bili-live-keeper/runtime/stream.env`.

Then systemd bridge logic updates the songbot with the fresh key.

## Primary service flow

```text
bili-live-keeper.service
    -> writes /opt/bili-live-keeper/runtime/stream.env

bili-songbot-stream-sync.path
    -> detects stream.env change

bili-songbot-stream-sync.service
    -> runs /usr/local/sbin/bili-songbot-use-keeper-stream

bili-songbot.service
    -> pushes the actual songbot livestream
```

## Important

`bili-live-keeper-push.service` must remain disabled/masked. The keeper must not push black/silent video because the songbot is the real pusher.

## Quick status

```bash
systemctl status bili-live-keeper.service --no-pager
systemctl status bili-songbot-stream-sync.path --no-pager
systemctl status bili-songbot.service --no-pager
systemctl status bili-live-keeper-push.service --no-pager || true
ss -antp | grep -E "1935|ffmpeg|live-push" || true
curl -fsS http://127.0.0.1:8787/healthz || true
```

Expected:

```text
bili-live-keeper.service          active/running
bili-songbot-stream-sync.path     active/waiting
bili-songbot.service              active/running
bili-live-keeper-push.service     masked/inactive/not found
RTMP connection                   ESTAB
```
