# OPERATION_LOG.md

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
