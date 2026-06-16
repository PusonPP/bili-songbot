# CHANGELOG_CODEX.md

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
