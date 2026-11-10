# OPERATION_LOG.md

## 2026-11-10 21:03 UTC - Remaining lyrics: text deployment and audio checks

User requested remaining ten songs and full-catalog line-by-line listening,
without unnecessary live interruption. The current tool interface cannot
directly audition audio; this was disclosed. Text review, actual PCM checks and
independent local ASR are evidence, NOT a listening certificate.

- Read operating documents; initial health OK. Existing unrelated uncommitted
  changes in these logs (37/51 lines) are preserved and excluded from staging.
- Backups before edits: `.bak.20261110T203800Z` for the audit, both logs and
  correction YAML. Created audio-integrity/ASR scripts; all outputs are ignored.
- Installed diagnostic-only faster-whisper 1.2.1 and soundfile 0.13.1 in
  runtime/lyrics-audit-venv; no production/global dependency change. Downloaded
  public Systran/faster-whisper-small revision
  536b0662742c02347bc0e980a01041f333bce120 without account credentials. Single
  CPU thread, nice 15. PyAV 19 removed metadata_errors, so use verified FFmpeg
  PCM decoding for ASR instead; no lyrics prompt and no automatic deployment.
- All 42 originals fully decoded. Forty clean; song_028's PCM count/MD5 match
  despite a decoder error; song_030 is missing 156984 sample frames at 44100 Hz.
  Independent libsndfile also fails on song_030. ZIP CRC valid and SHA256 matches
  extracted source. Both current and May backup videos contain only 312.947s of
  audio too. No complete local replacement was found by filename search.
- User answered to skip song_030 pending their replacement; do not pad, change
  its declared duration to conceal damage, or attempt further recovery now.
- Reviewed all 42 supplied text pairs and added source-guarded corrections.
  Fifteen songs changed; 107 correction entries in total, 71 active. Kept all
  titles/aliases. Six pending songs received source-text fixes only, not media.
- User authorized a blind listening capability test with one subagent. Provided
  a 23.87s local clip; the agent explicitly could not hear it. Closed that agent,
  did not run listening batches or mislabel ASR as direct audition.
- Fully inspected the four reference mappings (003/004/016/023), verified public
  source IDs against cached lyric bytes, and recorded 151 groups with explicit
  blocking flags. Actual import of all four produced blocked_reference, no ASS.
- Built textfix release for fifteen songs: nine valid ASS tracks and six
  pending TXT pairs. Compared every event start/end against active ASS, rendered
  nine real frames, and confirmed twelve changed display cues with no retiming.
  At 21:03:04 UTC, while an unaffected song was playing, the guarded local
  activate_textfix.py backed up old ASS and atomically linked to the new release.
  YAML now points to the new files for later starts; running renderer resolves
  links per chunk. Original audio, clean masters, durations and aliases unchanged.
  At 21:09 UTC song_021's active renderer used 20261110-v3-textfix, same main PID.
- Additional backups: build_lyric_media.py .bak.20261110T203800Z, songs.yaml
  and nine ASS .bak.20261110T205500Z, tests/test_lyrics.py .bak.20261110T210404Z.
  Runtime deployment manifest records backup paths and new ASS hashes. Existing
  old release ASS paths are now links, not silently overwritten subtitle text.
- Actual waveform comparison of 41 original/current playback pairs: 3 x 5s
  windows per song (roughly 10/50/90%), 8 kHz mono, normalized cross-correlation.
  All 123 peaks at zero relative offset, coefficient range .988657-.999850.
  song_030 was skipped per user request. This does not certify whole-track,
  platform-received synchronization or lyric vocal timing.

Commands and checks at this checkpoint:

- `.venv/bin/python scripts/audit_lyric_audio.py --manifest runtime/lyrics-import/catalog-map.json --output runtime/lyrics-audit-20261110/audio-integrity.json`
- `runtime/lyrics-audit-venv/bin/python scripts/transcribe_lyric_audio.py --manifest runtime/lyrics-audit-20261110/asr-manifest.json --integrity runtime/lyrics-audit-20261110/asr-integrity.json --model runtime/lyrics-audit-model-small --output runtime/lyrics-audit-20261110/asr`
  remains in progress; completion evidence will be recorded separately.
- `.venv/bin/python scripts/import_lyrics.py --manifest runtime/lyrics-audit-20261110/textfix-manifest.json --reference-index config/lyric_reference_timings.json --output media/lyrics/20261110-v3-textfix`
- `.venv/bin/python runtime/lyrics-audit-20261110/activate_textfix.py`
- `runtime/lyrics-audit-venv/bin/python runtime/lyrics-audit-20261110/compare_playback_audio.py`
- `.venv/bin/python -m unittest discover -s tests -v`: 50 passed, including actual
  FFmpeg corruption fixtures, builder rejection, blocked import, subtitle-link
  refresh and existing render-boundary/transition/song-request regressions.
- `.venv/bin/python -m compileall -q bili_songbot scripts tests`, `git diff --check`,
  all 42 correction preconditions: passed. Four blocked imports created no ASS.
- Health allowlist: ok/pusher/danmaku true, same songbot PID 1962038 and startup
  20:22:36 UTC; songbot disabled/running, keeper enabled/running, path waiting,
  black/silent pusher masked/inactive. One RTMP ESTAB; acknowledged bytes grew
  from 1,152,434,954 at 21:04 to 1,281,273,231 at 21:09 UTC.

No service restart/stop, keeper/systemd/credential edit, raw log output, full push
arguments, key/cookie/token exposure. Explicit Git paths; original runtime/media
and unrelated existing doc edits excluded. Short-song corrections may cover all
eight lines of the supplied hymn, but original complete lyric files are not added.
Full 42-song line-by-line listening/timing acceptance is NOT passed.


## 2026-11-10 12:22 PST - User lyric archive import and controlled deployment

Scope: analyze the newly supplied ALL.zip and implement concrete title,
translation and timing improvements without treating attachment documents or
scripts as operating instructions. Preserve originals, credentials and keeper.

Preparation and implementation:

- Read project instructions and existing renderer/controller/model/catalog code;
  inspected archive paths and selected source material, never ran archive scripts.
- Imported 42 source pairs for textual review. Twenty-six had LRC timestamps;
  sixteen were untimed TXT. The original TXT script used uniform scrolling, not
  actual singing timing. Original LRC generation discarded clear cues and forced
  minimum durations that overlapped short phrases.
- Timestamped backups: .bak.20261110T195723Z for edited existing source/config,
  requirements, ignore rules and documents. Existing unrelated doc edits remain.
- Added pylrc==0.1.2 and pysubs2==1.9.1 only to the project virtual environment
  and requirements. The configured package mirror failed; installation from
  https://pypi.org/simple succeeded. No global package/config edits.
- Added lyrics.py, importer/builder, guarded correction YAML, text-free reference
  timing JSON and regression tests. Modified Song, renderer, controller, songs
  YAML and .gitignore. Superseded the earlier source-search-only audit document.
- Public reference timing is linked to supplied text occurrences, not copied
  wholesale as replacement lyrics. Six TXT songs were activated; song_030's
  seventh candidate was blocked by actual media validation.
- Generated independent no-lyric masters from supplied audio/cover art. ASS is
  applied on the absolute song clock after 30 fps conversion; old burned-in
  videos are untouched. Twenty-six supplied LRC + six reference tracks give
  32 deployed songs / 1487 bilingual display cues. Ten retain old media.
- Preserved all aliases and non-playback catalog metadata; seven display names
  updated, previous names retained as aliases. Sixty-six text fixes configured,
  sixty-one active; five stay in pending source material.
- Confirmed song_030's declared 316.506667s differs from decoded 13,800,960
  stereo frames at 44.1 kHz (312.946939s). Kept the original/candidate for audit,
  did not relax validation, pad missing audio or deploy the incomplete source.

Commands and verification:

- `.venv/bin/python scripts/import_lyrics.py ...`: strict occurrence pairing,
  bounds, clear cues, correction preconditions and safe ASS layout validated.
- `.venv/bin/python scripts/build_lyric_media.py media/lyrics/20261110-v1` and
  `... media/lyrics/20261110-v2`: low-priority local FFmpeg builds; 32 valid masters.
- `.venv/bin/python -m unittest discover -s tests -v`: 37 passed, including all
  previous song request tests, reference-group coverage, actual FFmpeg pixel
  checks around 20s, and full-tail / zero-next-offset transition regressions.
- `.venv/bin/python -m compileall -q bili_songbot scripts/import_lyrics.py scripts/build_lyric_media.py tests` and
  `git diff --check`: passed. No units edited, so no daemon-reload or unit changes.
- ffprobe / byte hashes / ASS round trips checked all selected assets; actual
  frames rendered for all 32. Sample 20s chunk rendered in 6.66s under a one-thread
  diagnostic cap. Corrected an early diagnostic inference: ffprobe's estimated
  audio duration was not evidence of loss; actual AAC packet span was 20.032s.
- Announced and ran exactly `systemctl restart bili-songbot.service` once.
  Main process started 2026-11-10 20:22:36 UTC (12:22:36 PST). No keeper, path,
  bridge, unit, cookie or stream-env modifications; no black/silent pusher.
- After deployment health reported ok, pusher and danmaku true. Running song_007
  renderer confirmed clean master + external ASS + absolute clock. One RTMP
  socket remained established; acknowledged bytes increased 14,248,522 to
  21,582,189 over 15s. Songbot remains boot-disabled; keeper/path active;
  keeper-push remains masked/inactive. Platform API checks may be rate-limited;
  connection/process health alone is not a received-video timing certification.
- Retried the unauthenticated platform request with normal browser headers:
  API code=0, room live=true. Keeper's latest 40 heartbeat records also report
  live=true. No ERROR/CRITICAL/Traceback after the latest songbot startup.
- Fresh-import regression confirmed blocked song_030 produces no deployable ASS.

Secrets: never printed stream URLs, keys, cookies, tokens or raw FFmpeg process
arguments. Runtime/log checks output selected nonsecret fields and counts only.
Git staging uses explicit paths and only this turn's additions to the two logs;
complete lyrics/media/diagnostics and preexisting unrelated doc edits excluded.

Acceptance: engineering regression and deployed asset structure PASS. Complete
42-song translation and line-by-line vocal synchronization acceptance NOT PASS;
ten media replacements, seven inferred final holds and long LRC display spans
remain explicitly pending in docs/LYRICS_AUDIT.md. No claim of full listening.

## 2026-11-10 10:48 PST - Server-wide lyric source investigation

The user asked for complete title/translation/timing review, then explicitly
requested searching the whole server for existing LRC and rolling-lyric TXT.

- Read the operating documents and playback/preprocessing/UI code.
- Used rg filename scans, structured TXT classification and ZIP directory
  inspection, plus tar listing of the old songbot backup and Git path history.
- Scanned about 782,235 visible paths without traversal errors. No editable
  subtitle file found. Of 5,607 TXT paths, inspected 193 non-sensitive candidates;
  matching project files held UI text, not song lyrics. Avoided credential files.
- Inspected 56 ZIP directories and the 4.57 GB songbot TAR.GZ backup. Did not
  inspect every unrelated project TAR or access encrypted/unmounted stores.
- ffprobe checked all 84 source/playback files for the 42-song catalog: zero
  subtitle streams. Generated ignored diagnostics under runtime/lyrics-audit/.
- Recorded findings, source links, limitations and pending acceptance in
  docs/LYRICS_AUDIT.md. Requested a remembered filename/path or original files.
- Reviewed a potential transition-head audio omission in code, but did not
  represent it as a reproduced/fixed defect or modify production playback.
- No application code, catalog, media, unit or credential changes. No service
  restart/stop. Healthz allowlist remained ok=true, pusher_running=true and
  danmaku_connected=true. No raw logs, stream URLs or credential values printed.
- Backed up both existing logs with suffix .bak.2026-11-10_184825Z. Preserve
  unrelated preexisting entries and stage only this new audit documentation.

Result: source inventory complete for the documented scope; full lyric and
line-timing acceptance NOT passed. Do not imply that media metadata proves
each lyric's correctness or alignment. Await source-file location information.

## 2026-11-10 06:11 UTC - Song recognition aliases and matcher corrections

Scope: improve original-title and intuitive Chinese song requests for all 42
existing songs. Do not change playback assets, queue policy, keeper, units,
stream credentials, or unrelated maintenance records already in the worktree.

Research and changes:

- Read project operating/safety documentation, matcher, queue, configuration,
  controller and storage. Checked all 42 local video title frames and official
  discographies, plus indexed station uploads; documented sources and limits in
  docs/SONG_REQUEST_ALIASES.md. Public uploader enumeration was rate-limited;
  no credentials were used to bypass it. No claim of exhaustive subtitle review.
- Backed up matcher.py, songs.yaml and both operation documents with suffix
  .bak.2026-11-10_061121Z before editing.
- Appended 358 aliases only; all original aliases and non-alias metadata were
  verified unchanged. Normalized alias index: 453 before, 805 after.
- Fixed fuzzy ambiguity previously masked by multiple synonyms of one song;
  preserved exact matches ahead of version ambiguity. Stopped inverse substring
  matches on chat sentences. Fixed song_026 parsing and Unicode punctuation.
- Added tests/test_matcher.py with 18 offline tests. Tests use a temporary
  database and never send live danmaku or add requests to the production queue.

Validation commands and results:

- `.venv/bin/python -m unittest discover -s tests -v`: 18 tests passed, including
  all configured aliases/display names/IDs and all 42 original titles/keywords.
- `.venv/bin/python -m compileall -q bili_songbot tests`: passed.
- `git diff --check`: passed.
- Structured comparison against the backup confirmed only alias additions in
  songs.yaml. A curated 42-keyword sample improved from 11 correct (7 exact)
  to 42 correct/exact; this is not a production accuracy measurement.
- Pre-deployment healthz allowlist: ok=true, pusher_running=true,
  danmaku_connected=true; room API code=0/live_status=1; FFmpeg RTMP ESTAB.
- Songbot active/disabled for boot; keeper active/enabled; sync path waiting;
  black/silent keeper pusher masked/inactive. Root filesystem had 26 GiB free.

Deployment and follow-up:

- Announced `systemctl restart bili-songbot.service` and its brief stream
  reconnect before execution; ran it once at 06:20:20 UTC. The active stream
  session had just been confirmed valid; no saved stale session was started.
- New songbot process started at 06:20:21 UTC. Health checks returned ok=true,
  pusher_running=true and danmaku_connected=true; room API live_status=1.
- Same new FFmpeg RTMP connection remained ESTAB; acknowledged bytes increased
  from 3,777,215 to 21,837,678 by 06:21:09 UTC. A viewer request entered the
  queue during observation; no synthetic request was sent to the live service.
- Post-startup log marker counts for RTMP_BROKEN_PIPE_FATAL, Broken pipe,
  End of file, Traceback and playback/danmaku failures were all zero. Only
  allowlisted health fields and error counts were displayed, not raw logs.
- Keeper PID unchanged; sync path active/waiting; songbot disabled for boot;
  black/silent keeper pusher masked/inactive. No other service was restarted.
- No secrets or complete push URLs were printed; sensitive files untouched.
  Only explicit task paths are staged, with this new document section staged
  separately from the unrelated preexisting uncommitted entries below.

Remaining limits: alternate translations not yet in the curated catalog may
still need explicit aliases; broad or version-ambiguous requests are rejected.
The 18 offline tests and live health checks do not substitute for exhaustive
human evaluation of future danmaku wording. Deployment needed one reconnect.

## 2026-11-02 22:18 UTC - User-authorized livestream resume

The user explicitly asked to resume broadcasting, superseding the intentional
pause recorded below. Preflight found the room offline, keeper/path/songbot
inactive and disabled, no RTMP connection, and about 28 GiB free on root.

Actions:

- Ran `systemctl enable --now bili-songbot-stream-sync.path`, then
  `systemctl enable --now bili-live-keeper.service` at 22:18:15 UTC.
- Allowed keeper's two-check offline confirmation and existing browser workflow
  to obtain a fresh session for the stream-sync bridge.
- Retained songbot's disabled boot state and the keeper pusher's masked state.
- Backed up these documents with suffix `.bak.2026-11-02_221839Z`.
- No application code or unit file contents were changed. Existing unrelated
  uncommitted maintenance records were preserved.

Verification:

- Keeper confirmed the configured area, started the room, and wrote fresh
  stream.env at 22:19:46 UTC. The path/bridge applied it and started songbot.
- Room API returned `live=true`, `room_live_status_1` at 22:20:14 UTC.
- Healthz returned `ok=true`, `pusher_running=true`, `danmaku_connected=true`,
  and RTMP output mode on both checks; process uptime continued increasing.
- The same FFmpeg RTMP connection remained ESTAB. Acknowledged bytes increased
  from about 9.1 MB to 22.4 MB during the follow-up observation.
- Keeper was active/running and enabled; sync path was active/waiting and
  enabled. Songbot was active/running but disabled for boot. The keeper's
  black/silent pusher stayed masked/inactive.
- Both runtime environment files retained mode 0600. Credentials and full push
  URLs were filtered from output and were not staged. No logs were truncated.
- This was an operational resume without source/unit changes; validation used
  service state, the platform API, healthz, RTMP counters, and document diff checks.

## 2026-11-02 06:53 UTC - Intentional project pause

User requested pausing this project and stopping the live stream. The inactive
state is intentional. Do not run recovery or start-once until the user asks to
resume. Existing uncommitted maintenance entries were preserved.

Actions:

- Ran `systemctl disable --now bili-songbot-stream-sync.path bili-live-keeper.service`
  to stop automatic recovery and remove their boot enablement.
- Ran `systemctl stop bili-songbot-stream-sync.service bili-songbot.service`
  after stopping the producers of restart requests.
- Keeper CLI `stop-once` initially could not click the close-live control.
  Used the existing BiliLiveBrowser helpers as the keeper user to dismiss the
  transient popup, click close-live, confirm, and wait for the stopped state.
  This was a one-shot operation; no source change was required.
- Backed up these documents with suffix `.bak.2026-11-02_065318Z` before editing.

Verification:

- Dashboard reported `detected_start_live_button`; room API reported
  `live=false`, `room_live_status_0` at 2026-11-02 06:53:26 UTC.
- Keeper, songbot, sync path, and sync service were all inactive/dead. Keeper,
  songbot, and sync path were disabled; sync service remained static.
- Keeper black/silent pusher remained masked/inactive.
- No FFmpeg process, TCP connection to port 1935, or listener on port 8787 remained.
- No matching project timer or active root crontab entry was found.
- No service was restarted. Source/media/configuration were retained; no logs
  were truncated. Credential values and complete push URLs were not emitted.

Resume only upon a later explicit user request:

- Enable/start `bili-songbot-stream-sync.path`, then `bili-live-keeper.service`.
- Let keeper reopen the room and write a fresh stream environment. The bridge
  then starts songbot; do not directly start songbot using the saved old session.
- Recheck the room API, health endpoint, and RTMP transmission before reporting
  recovery. The existing environment files are retained but are not proof of a
  currently valid live session.

## 2026-09-14 CST - Recover stalled live-keeper

The room was offline, songbot inactive, and no RTMP socket existed. Songbot logged
RTMP Broken pipe at 2026-09-13 14:03:39 CST. Keeper was running but its browser
startup repeatedly failed with the Playwright sync API / asyncio loop error.
Disk-full errors also appeared; root had about 1.7 GiB available at inspection.
Earlier logs were incomplete, so the first browser startup failure is unconfirmed.

Reproduced an event-loop leak using an invalid Chromium executable, without
loading account cookies or visiting Bilibili. A failed context-manager entry did
not call close(), leaving the Playwright loop running and blocking future starts.
Added exception cleanup in production browser.py and its paired source snapshot,
plus regression tests. Backups use suffix `.bak.2026-09-14_025834`.
Existing uncommitted August maintenance entries were preserved.

Recovery and verification:

- `systemctl restart bili-live-keeper.service` at 03:00:22 CST loaded the fix and
  released the stuck process. No systemd unit files were changed.
- After two offline confirmations, keeper opened the room and wrote fresh
  stream.env at 03:01:52 CST. The path/bridge applied it and started songbot.
- `python -m unittest discover -s paired/live-keeper/tests -v`: two tests passed.
  Python compilation, production/snapshot comparison, and git diff checks passed.
- Keeper API check returned live=true; healthz returned ok=true with connected
  danmaku and a running pusher. FFmpeg RTMP was ESTAB with increasing bytes_acked.
- Keeper and songbot were active/running; the sync path was active/waiting.
  Songbot remained disabled for boot; the black/silent pusher stayed masked/inactive.
- Root usage remained 99%, with about 1.7 GiB available. Read-only size checks
  identified roughly 43 GiB in /var/lib/secure-cloud-drive and 19 GiB in
  /var/lib/containerd. These are outside this repair and were not modified.
- Log inspection was redacted; no credentials, full push URLs, runtime logs,
  real environment files, or cookies were staged. No logs were truncated.

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
