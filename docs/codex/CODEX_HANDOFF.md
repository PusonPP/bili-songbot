# CODEX_HANDOFF.md

## Current known architecture

```text
/srv/bili-songbot
```

Main project. Responsible for media rendering, danmaku handling, queue logic, overlay UI, and RTMP push.

```text
/opt/bili-live-keeper
```

Paired project. Responsible for live status detection, automatic Bilibili start-live, and fresh RTMP stream info generation.

## Integration

```text
/opt/bili-live-keeper/runtime/stream.env
    -> watched by bili-songbot-stream-sync.path
    -> consumed by /usr/local/sbin/bili-songbot-use-keeper-stream
    -> updates /srv/bili-songbot/config/.env
    -> restarts bili-songbot.service
```

## Normal state

```text
bili-live-keeper.service          active/running
bili-songbot-stream-sync.path     active/waiting
bili-songbot.service              active/running
bili-live-keeper-push.service     masked/inactive
```

## Do not forget

- Do not expose RTMP key or cookies.
- Do not enable keeper push service.
- Do not enable songbot for boot startup unless architecture changes.
- Use root carefully.
- Backup before edits.
