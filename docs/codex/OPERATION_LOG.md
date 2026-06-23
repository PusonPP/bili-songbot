# OPERATION_LOG.md

## 2026-06-23 11:00:08 UTC

Added a festival notice to the live overlay announcement text.

Actions:

- Updated `config/app.yaml` so `ui.right_top_notice` starts with `＊当前正在举办 【佐贺偶像是传奇梦幻银河祭】二创庆典`.
- Updated `bili_songbot/ui_layer.py` so fallback PNG notice wrapping respects explicit newline breaks.

Safety:

- Did not read or edit real `.env`, `stream.env`, cookies, or tokens.
- Did not restart or stop any service.
- Did not expose RTMP stream keys or full push URLs.

## 2026-06-16 15:10:51 UTC

Prepared `/srv/bili-songbot` for initial Git publication to `PusonPP/bili-songbot.git`.

Actions:

- Planned a single repository rooted at `/srv/bili-songbot`.
- Kept `/opt/bili-live-keeper` runtime untouched and copied only a sanitized source snapshot into `paired/live-keeper/`.
- Expanded Git ignore rules for secrets, runtime files, logs, backups, cookies, generated media, and caches.
- Planned to stage only source, scripts, docs, examples, and safe systemd/bridge samples.

Safety:

- Did not read or stage real `.env`, `stream.env`, cookies, logs, or runtime databases.
- Did not restart, stop, enable, or disable any service.
- Did not expose RTMP stream keys or full push URLs.

## 2026-06-16 14:55:42 UTC

Created Codex-ready documentation pack for `/srv/bili-songbot`.

Purpose:

- Let Codex understand the songbot project immediately.
- Explain paired live-keeper integration.
- Document service topology, secrets handling, recovery procedures, and root-account safety rules.

No runtime code changes.
