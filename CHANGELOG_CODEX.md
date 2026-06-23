# CHANGELOG_CODEX.md

## 2026-06-23 11:30:35 UTC — Alternate right-top overlay notices

Changed the right-top live overlay notice from a stacked two-line block to a two-item rotation.

Details:

- Wrote the first two notice lines to separate runtime text files.
- Updated the FFmpeg overlay filter to alternate them every 30 seconds.
- Added a 1.5 second crossfade at each switch so the next notice fades in while the previous one fades out.
- Restarted `bili-songbot.service` and verified the new FFmpeg overlay filter, health endpoint, split notice files, and RTMP connection.

This keeps the notice from covering song title text near the top of the video.

## 2026-06-23 11:23:34 UTC — Make overlay notice updates reload from config

Fixed the festival notice not appearing on the current stream.

Root cause:

- The running `bili-songbot.service` process had loaded `config/app.yaml` before the festival notice was added.
- `runtime/ui_overlay.notice.txt` still contained the old notice, and the running process could overwrite manual edits during later UI refreshes.

Changes:

- Refreshed `runtime/ui_overlay.notice.txt` with the festival notice for the currently running FFmpeg overlay.
- Updated `bili_songbot/ui_layer.py` so notice text is read from `config/app.yaml` each time the overlay runtime text files are written.
- Restarted `bili-songbot.service` to load the new overlay notice behavior into the currently running stream.

No secrets were read or changed.

## 2026-06-23 11:00:08 UTC — Add festival notice to live overlay

Added the current event notice to the live overlay right-top announcement:

- `＊当前正在举办 【佐贺偶像是传奇梦幻银河祭】二创庆典`

Also updated the fallback PNG overlay text wrapping helper to respect explicit newline breaks in notices.

No services were restarted or stopped. No secrets were read or changed.

## 2026-06-16 15:10:51 UTC — Initial Git publication preparation

Prepared the project for a first safe Git commit and GitHub push.

Included:

- Expanded `.gitignore` to exclude secrets, runtime state, logs, backups, media files, caches, cookies, and generated artifacts.
- Added a sanitized source snapshot of the paired live-keeper project under `paired/live-keeper/`.
- Updated repository systemd samples to match the current stream-sync topology.
- Added the stream-sync bridge script sample under `scripts/`.

No live services were restarted or stopped. Real `.env`, `stream.env`, cookies, logs, runtime state, media files, and stream keys were not staged.

## 2026-06-16 14:55:42 UTC — Codex-ready documentation pack

Added Codex handoff and operational documentation for the Bilibili live songbot project.

Included:

- `AGENTS.md`
- `AGENT.MD`
- `AGENT.md`
- `README_CODEX.md`
- `PROJECT_CONTEXT.md`
- `OPERATIONS_RUNBOOK.md`
- `SYSTEMD_TOPOLOGY.md`
- `SAFETY_AND_SECRETS.md`
- `TASK_GUIDE_FOR_CODEX.md`
- `CODEX_LOGIN_ROOT_GUIDE.md`
- `docs/codex/OPERATION_LOG.md`
- `docs/codex/CODEX_HANDOFF.md`
- helper scripts under `scripts/`

No business logic changes are included in this pack.
