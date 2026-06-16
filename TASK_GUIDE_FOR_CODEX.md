# TASK_GUIDE_FOR_CODEX.md

## Common task: diagnose current live status

Run:

```bash
bash /srv/bili-songbot/scripts/codex_diagnose_all_live.sh
```

If the script is unavailable, run checks manually:

```bash
systemctl status bili-live-keeper.service --no-pager
systemctl status bili-songbot-stream-sync.path --no-pager
systemctl status bili-songbot.service --no-pager
ss -antp | grep -E "1935|ffmpeg|live-push" || true
```

## Common task: change songbot code

1. Backup files.
2. Edit minimal files.
3. Run py_compile.
4. Restart only if needed.
5. Check logs and RTMP.

```bash
cd /srv/bili-songbot
source .venv/bin/activate
python3 -m py_compile $(find bili_songbot -name '*.py')
```

## Common task: change live-keeper code

Only do this if the issue is about auto-start, cookie, Chromium, Bilibili dashboard, or stream.env.

```bash
cd /opt/bili-live-keeper
/opt/bili-live-keeper/.venv/bin/python -m py_compile $(find src -name '*.py')
systemctl restart bili-live-keeper.service
```

## Common task: test keeper manually

```bash
cd /opt/bili-live-keeper
sudo -u bili-live-keeper env -u DISPLAY -u XAUTHORITY \
  HOME=/var/lib/bili-live-keeper \
  XDG_CACHE_HOME=/var/lib/bili-live-keeper/.cache \
  /opt/bili-live-keeper/.venv/bin/python -m bili_live_keeper.cli check
```

Dry run:

```bash
cd /opt/bili-live-keeper
sudo -u bili-live-keeper env -u DISPLAY -u XAUTHORITY \
  HOME=/var/lib/bili-live-keeper \
  XDG_CACHE_HOME=/var/lib/bili-live-keeper/.cache \
  /opt/bili-live-keeper/.venv/bin/python -m bili_live_keeper.cli start-once --dry-run
```

Real start:

```bash
cd /opt/bili-live-keeper
sudo -u bili-live-keeper env -u DISPLAY -u XAUTHORITY \
  HOME=/var/lib/bili-live-keeper \
  XDG_CACHE_HOME=/var/lib/bili-live-keeper/.cache \
  /opt/bili-live-keeper/.venv/bin/python -m bili_live_keeper.cli start-once
```

## Common task: restart songbot with current stream.env

```bash
systemctl start bili-songbot-stream-sync.service
```

## Common task: avoid Xshell X11 popups

Run keeper/Playwright commands with:

```bash
env -u DISPLAY -u XAUTHORITY
```

The service also sets:

```text
DISPLAY=
XAUTHORITY=
```
