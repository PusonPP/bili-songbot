# CODEX_LOGIN_ROOT_GUIDE.md

## Account model

Codex logs into the server as:

```text
root
```

This is intentional for this project because it needs access to:

- `/srv/bili-songbot`
- `/opt/bili-live-keeper`
- `/etc/systemd/system/*.service`
- `/usr/local/sbin/bili-songbot-use-keeper-stream`
- service logs and runtime files

## Primary working directory

```text
/srv/bili-songbot
```

Codex should start there for most tasks.

## Secondary project

```text
/opt/bili-live-keeper
```

Codex may inspect or modify this only for:

- Bilibili live status detection.
- Automatic start-live flow.
- Chromium/Playwright issues.
- biliup login/cookies.
- RTMP stream.env generation.
- Integration with songbot.

## Root safety rules

Being root does not mean changing everything is allowed.

Before any disruptive operation:

- Explain what will be stopped/restarted.
- Avoid killing active stream processes unless required.
- Avoid package upgrades unless required.
- Avoid deleting media files.
- Avoid editing unrelated services.
- Keep secrets masked.

## Allowed systemd operations

Allowed when relevant:

```bash
systemctl status ...
systemctl restart bili-live-keeper.service
systemctl start bili-songbot-stream-sync.service
systemctl status bili-songbot.service
systemctl daemon-reload
systemd-analyze verify ...
```

Be careful with:

```bash
systemctl restart bili-songbot.service
systemctl stop bili-songbot.service
```

These interrupt live streaming.
