# CHANGELOG_CODEX.md

## 2026-11-10 UTC - Complete machine-evidence ledger, not listening acceptance

- Completed independent local ASR for 41 songs; user-deferred song_030 skipped.
  Recorded 1960 source/display rows, source hashes and sampled waveform evidence.
- Inspecting extreme apparent offsets exposed cross-verse/repeated-chorus ASR
  matches. Excluded repeated source phrases and matched-word gaps over 3 seconds
  from automatic anchors; added two regressions, now 52 tests passing.
- Final ledger has 263 candidate anchors, 201 existing-start comparisons and
  41 differences over 750ms. These are unconfirmed machine discrepancies, not
  approved retiming. No native listening or vocal-end certification is claimed.
- Published text-free per-track statistics in docs/lyrics-review-20261110.json;
  full local line sheets remain ignored under runtime/.../review-final-v2.
- Prior text hotfix and safeguards were pushed as dc6fa6d. No further production
  edits, subtitle timing changes, service restarts or credential exposure.

## 2026-11-10 21:03 UTC - Lyric text hotfix and audio integrity safeguards

- Rechecked all 42 supplied lyric/translation pairs and decoded every original
  audio file. Confirmed song_030 has invalid FLAC data, missing PCM samples and
  a mismatching checksum; its ZIP member is identical, not an extraction error.
  User subsequently requested deferring this song until replacement audio arrives.
- Isolated offline ASR dependencies/models under runtime; production environment,
  keeper, credentials and services are unchanged. ASR is not listening acceptance.
- Added guarded textual fixes including REVENGE's surrender/happiness homophone,
  Survive's Dive/Die error, short-line translation order and the inaccurate hymn
  paraphrase in song_038. Correction rules total 107; 71 apply to active tracks.
- Hot-updated nine ASS tracks / twelve display cues at 21:03:04 UTC, with exact
  event times unchanged. Six other text revisions remain pending with old media.
  The same running process rendered the new song_021 ASS; no service restart.
- Added four explicitly blocked reference candidates / 151 source-line groups.
  A user-authorized blind audio probe failed native listening access, so no
  listening batches ran. The entire 42-song listening acceptance remains open.
- Added actual PCM/sample-count/checksum validation before new master builds;
  FFmpeg exit-zero corruption cannot pass. Fifty tests and source guards pass.
- Waveform samples from 41 tracks / 123 windows match current playback audio
  with zero detected offset; this is sampled signal comparison, not listening.
- Full-catalog local ASR evidence is still running at this checkpoint. Details
  and remaining blockers are in docs/LYRICS_REVIEW_20261110.md. No secrets,
  original full lyric files, media or runtime artifacts are staged.


## 2026-11-10 12:22 PST - Import editable lyrics and repair playback timing

- Inspected user-supplied ALL.zip without executing its scripts: 42 audio files,
  42 covers, 26 LRC, 16 TXT and 42 Chinese translations. Originals are preserved.
- Added strict bilingual LRC import, explicit reference phrase mappings, ASS
  generation, clean-master building and optional external subtitles in playback.
- Deployed 32 songs / 1487 bilingual cues, including six formerly untimed TXT
  songs. The other ten keep their original videos; no invented uniform timing.
- Added 66 guarded text corrections; 61 appear in deployed subtitle tracks.
  Preserved familiar English names, station upload titles and every old alias.
- Fixed short-cue overlap, lost instrumental clears, repeated-text translation
  pairing, timestamp formatting and subtitle clock resets at chunk boundaries.
- Silent transitions now hold the next first frame and consume no song intro;
  outgoing songs play to their end instead of losing a fixed transition tail.
- Rejected song_030 during media validation: its FLAC header claims 316.507s
  but actual PCM ends at 312.947s. Kept old playback and recorded the blocker.
- 37 tests passed, including real FFmpeg subtitle boundary pixel checks; all 32
  selected masters passed media checks and offline frame rendering. Sources,
  remaining long holds and incomplete line-by-line listening are documented in
  docs/LYRICS_AUDIT.md. Full-catalog linguistic/timing acceptance is NOT passed.
- Restarted only bili-songbot.service at 20:22:36 UTC / 12:22:36 PST; health,
  danmaku, active external ASS rendering and increasing RTMP bytes verified.
- No keeper/unit/credential changes. No secrets, full lyrics, audio, images,
  generated subtitles, runtime diagnostics or unrelated doc edits committed.

## 2026-11-10 10:48 PST - Inventory missing lyric/subtitle sources

- Extended the user-requested search to visible server files, TXT candidates,
  56 ZIP directories, the older songbot TAR backup and project Git history.
- No editable LRC/ASS/SRT/SSA/VTT or lyric TXT was found. UI text files are
  current-title/queue/notice data, not song lyrics. No credential contents shown.
- Probed all 42 source and 42 playback videos: no subtitle streams. Recorded
  source-location limits and pending line-by-line verification in lyrics audit
  documentation at docs/LYRICS_AUDIT.md; no claim of lyric/timing completion.
- No source/config/media changes or service restarts. Live health remained OK.
- Preserved unrelated preexisting document edits; only this audit is committed.

## 2026-11-10 06:11 UTC - Expand intuitive song request recognition

- Added 358 alias entries across all 42 songs, preserving every previous alias
  and all playback metadata. The index now has 805 normalized names/IDs.
- Added short Chinese/kanji keywords such as history, universe, squid, adventure,
  and version-specific names; original Japanese titles remain exact matches.
- Verified local video title frames, official track lists, and three public
  station uploads. Added the station's published history-song translation.
  Source links and research limitations are in docs/SONG_REQUEST_ALIASES.md.
- Normalized Unicode punctuation/copy-paste formatting, fixed command/ID parsing,
  ranked fuzzy candidates by distinct songs, and removed unrestricted matching
  of a short alias inside a longer chat sentence. Numeric IDs remain exact-only.
- Added 18 offline regression/integration tests. All pass, including every
  configured alias, all 42 original titles, version disambiguation, cooldown,
  duplicate requests, and rejection without queue mutation.
- The curated 42-keyword sample improved from 11/42 correct (7 exact) to 42/42
  exact. This is a regression sample, not a measured real-world accuracy rate.
- Backups use suffix .bak.2026-11-10_061121Z. Unrelated existing maintenance
  records are preserved. Deployment verification is recorded in OPERATION_LOG.
- No keeper/systemd/credential changes; no media or runtime files are committed.
- Restarted only songbot at 06:20:20 UTC to load the new matcher/catalog.
  Verified room live, health/danmaku/pusher healthy, and increasing RTMP bytes;
  keeper and sync path remained active, black/silent pusher masked/inactive.

## 2026-11-02 22:18 UTC - Resume livestream at user request

- The user explicitly requested resuming the project, ending the earlier pause.
- Preflight confirmed the room offline, paused services inactive/disabled,
  no RTMP socket, and about 28 GiB free on the root filesystem.
- Enabled/started the stream-sync path, then live-keeper, restoring automatic
  startup through the fresh-session bridge. Songbot remains disabled for boot.
- Keeper wrote the fresh stream environment at 22:19:46 UTC; the sync bridge
  applied it and started songbot. Room API confirmed live=true, health returned
  ok=true with danmaku/pusher active, and RTMP acknowledged bytes increased.
- Keeper is active/running and enabled; the sync path is active/waiting and
  enabled. The black/silent pusher remains masked/inactive.
- No application source or unit file contents were edited. Existing unrelated
  uncommitted maintenance entries are preserved.
- No credentials or full push URLs were exposed or committed.

## 2026-11-02 06:53 UTC - Project paused at user request

- Intentionally stopped the live stream and disabled automatic startup. This is
  a requested pause, not a service failure; resume only after the user asks.
- Disabled and stopped `bili-live-keeper.service` and
  `bili-songbot-stream-sync.path`; stopped stream-sync.service and songbot.service.
- Closed the Bilibili room after dismissing a dashboard popup. Both dashboard
  and room API confirmed offline. No FFmpeg process, RTMP socket, or health
  listener remained. The black/silent pusher remains masked/inactive.
- Kept source, media, configuration, and credentials intact. No service was
  restarted; no application code or unit file contents were changed.
- Recorded commands and guarded resume steps in docs/codex/OPERATION_LOG.md.
  Credentials and complete push URLs were not printed or committed.

## 2026-09-14 CST - Release Playwright after failed browser startup

- Confirmed songbot stopped after RTMP Broken pipe at 2026-09-13 14:03:39 CST.
- Keeper reported the room offline but repeatedly failed with a running asyncio
  loop error. Logs also contained disk-full errors; root usage was 99%.
- Reproduced the loop leak with an invalid browser executable, without account
  credentials or live-room actions.
- Added cleanup when browser context entry fails, including partial startup,
  and mirrored the production fix in the paired source snapshot.
- Added regression checks for repeated real Playwright launch failures and
  cleanup continuation when closing a disconnected context raises.
- Both regressions, Python compilation, and whitespace checks passed.
- Restarted keeper at 03:00:22 CST. At 03:01:52 CST it wrote a fresh stream
  environment and the existing stream-sync bridge started songbot.
- Verified API live=true, health ok=true, danmaku connected, and increasing RTMP
  acknowledged bytes. The black/silent pusher remains masked and inactive.
- Root filesystem remains 99% used, mainly by unrelated project/container data;
  no unrelated data was deleted. Low disk space remains an operational risk.
- No credentials, cookies, or complete push URLs were printed or staged.

## 2026-07-24 05:06:40 UTC — Recover live startup from dashboard popup

Fixed the paired live-keeper workflow after a new Bilibili dashboard popup blocked
the live-area selector.

Details:

- Confirmed the songbot stopped after Bilibili closed the RTMP connection with a
  `Broken pipe`.
- Identified the full-screen “cover ratio changed to 4:3” popup as the element
  intercepting clicks on “请选择直播分区”.
- Updated live-keeper to dismiss visible dashboard popup close controls before
  selecting the configured live area.
- Mirrored the sanitized live-keeper source change under `paired/live-keeper/`.
- Restarted only `bili-live-keeper.service`; the existing path/service bridge
  applied the fresh stream environment and started `bili-songbot.service`.
- Verified Bilibili API `live=true`, songbot health `ok=true`, and an established
  FFmpeg connection to RTMP port 1935.

No RTMP key, cookie, token, full push URL, or runtime secret was recorded.

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
