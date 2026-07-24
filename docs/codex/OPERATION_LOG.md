# OPERATION_LOG.md

## 2026-07-24 05:06:40 UTC

Investigated and recovered an interrupted Bilibili live session.

Findings:

- `bili-songbot.service` was inactive after FFmpeg received `Broken pipe`.
- Bilibili reported the room offline.
- `bili-live-keeper.service` repeatedly reached the live dashboard but could not
  click the live-area selector.
- Playwright trial-click diagnostics showed a new full-screen
  `link-popup-ctnr` cover-ratio reminder intercepting pointer events.
- Closing that popup made “请选择直播分区” immediately actionable.

Actions:

- Updated `/opt/bili-live-keeper/src/bili_live_keeper/browser.py` to dismiss
  visible live-dashboard popups before selecting the live area.
- Mirrored the sanitized source update to
  `paired/live-keeper/src/bili_live_keeper/browser.py`.
- Created timestamped backups before editing.
- Restarted only `bili-live-keeper.service` to load the fix.
- Observed the keeper close the popup, confirm `电台 / 聊天电台`, start the room,
  and write a fresh `runtime/stream.env`.
- Observed `bili-songbot-stream-sync.service` apply the new stream environment
  and start `bili-songbot.service`.

Verification:

- Bilibili API reported `live=true` with high confidence.
- `bili-live-keeper.service` and `bili-songbot.service` were active/running.
- `bili-songbot-stream-sync.path` was active/waiting.
- The songbot health endpoint returned `ok=true`, with danmaku and pusher active.
- FFmpeg held an established connection to RTMP port 1935.
- `bili-live-keeper-push.service` remained masked and inactive.

Safety:

- Kept `bili-live-keeper-push.service` masked and inactive.
- Did not print or record RTMP keys, cookies, tokens, or full push URLs.
- Restricted service recovery to the keeper and its existing stream-sync chain.

## 2026-06-23 11:30:35 UTC

Adjusted the right-top overlay notice to avoid covering the song title.

Actions:

- Updated `bili_songbot/ui_layer.py` to split the configured notice into two runtime files: `ui_overlay.notice.0.txt` and `ui_overlay.notice.1.txt`.
- Updated `bili_songbot/pusher.py` so FFmpeg alternates the two notice files every 30 seconds.
- Added 1.5 second crossfade alpha expressions at each switch.

Safety:

- Did not read or edit real `.env`, `stream.env`, cookies, or tokens.
- Restarted only `bili-songbot.service` after validation so the new FFmpeg overlay filter is loaded.
- Verified health endpoint, split notice files, active services, and masked RTMP connection after restart.

## 2026-06-23 11:23:34 UTC

Investigated why the festival notice was not visible in the live picture.

Findings:

- `config/app.yaml` contained the new festival notice.
- `runtime/ui_overlay.notice.txt` still contained the old notice.
- `bili-songbot.service` had been running since before the config change, so its in-memory config could keep writing the old notice to the runtime text file.

Actions:

- Updated `runtime/ui_overlay.notice.txt` directly so the current FFmpeg `drawtext reload=1` overlay can pick up the festival notice.
- Updated `bili_songbot/ui_layer.py` to reload `ui.right_top_notice` from `config/app.yaml` when writing runtime overlay text files.
- Restarted only `bili-songbot.service` so the running process uses the new code and config.
- Verified health endpoint, runtime notice text, and RTMP connection after restart.

Safety:

- Did not read or edit real `.env`, `stream.env`, cookies, or tokens.
- Did not restart keeper or stream-sync services.
- Did not expose RTMP stream keys or full push URLs.

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
