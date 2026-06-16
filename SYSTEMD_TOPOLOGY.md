# SYSTEMD_TOPOLOGY.md

## Services

### `bili-live-keeper.service`

Location:

```text
/etc/systemd/system/bili-live-keeper.service
```

Purpose:

- Runs `/opt/bili-live-keeper/.venv/bin/python -m bili_live_keeper.cli daemon`.
- Checks Bilibili live status periodically.
- If the room is offline, opens the live room and writes fresh stream info.

Expected:

```text
enabled
active/running
```

### `bili-songbot-stream-sync.path`

Location:

```text
/etc/systemd/system/bili-songbot-stream-sync.path
```

Purpose:

- Watches `/opt/bili-live-keeper/runtime/stream.env`.
- Triggers `bili-songbot-stream-sync.service`.

Expected:

```text
enabled
active/waiting
```

### `bili-songbot-stream-sync.service`

Location:

```text
/etc/systemd/system/bili-songbot-stream-sync.service
```

Purpose:

- Runs `/usr/local/sbin/bili-songbot-use-keeper-stream`.
- Updates `/srv/bili-songbot/config/.env`.
- Restarts `bili-songbot.service`.

Expected:

```text
inactive except when stream.env changes or manually triggered
```

### `bili-songbot.service`

Location:

```text
/etc/systemd/system/bili-songbot.service
```

Purpose:

- Runs the actual songbot.
- Starts FFmpeg pusher and renderer.
- Connects to Bilibili danmaku.

Expected:

```text
disabled
active/running when live
```

### `bili-live-keeper-push.service`

Purpose:

- Black/silent keepalive pusher from the keeper package.

Expected:

```text
masked or not found
inactive
```

Must not be enabled because the songbot is the real pusher.

## Why the stream-sync bridge is necessary

Bilibili may invalidate the old RTMP key when the live session drops. Restarting the songbot with the old key causes immediate `Broken pipe` or `End of file`.

The bridge ensures the songbot only restarts after a fresh key exists.
