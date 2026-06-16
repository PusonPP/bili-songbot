# PROJECT_CONTEXT.md

## What the user wants this system to do

The user wants a server-side 24/7 Bilibili live song-request station.

The stream should continue running without local computer involvement. It should:

- Play prepared song videos.
- Show a live overlay with current song, queue, request hints, and previews.
- Listen to Bilibili danmaku.
- Accept song requests.
- Handle request cooldowns and invalid requests.
- Return to random playback when the request queue is empty.
- Recover from Bilibili disconnects by automatically reopening the live room and refreshing the stream key.

## Server

The project runs on an Aliyun ECS Linux server. Codex usually logs in as `root`.

## Primary project

```text
/srv/bili-songbot
```

## Paired project

```text
/opt/bili-live-keeper
```

## Current operational model

The songbot service is intentionally not enabled for boot startup. It is started/restarted by the stream-sync bridge after a valid RTMP key exists.

The keeper service is enabled and should run continuously.

## Why `bili-songbot.service` is disabled

If songbot starts by itself after boot using an old RTMP key, FFmpeg may fail with:

```text
Broken pipe
End of file
frame=0
RTMP_BROKEN_PIPE_FATAL
start-limit-hit
```

Therefore, keep it disabled but allow it to be active/running when started by the stream sync process.

## RTMP key lifecycle

Fresh RTMP info comes from:

```text
/opt/bili-live-keeper/runtime/stream.env
```

The bridge script updates:

```text
/srv/bili-songbot/config/.env
```

and restarts:

```text
bili-songbot.service
```

## Known good live room area

```text
电台 / 聊天电台
```

## Known health endpoint

```text
http://127.0.0.1:8787/healthz
```

## Common log files

```text
/srv/bili-songbot/logs/systemd.log
journalctl -u bili-live-keeper.service
journalctl -u bili-songbot-stream-sync.service
```
