# INSTALL_CODEX_READY_PACK.md

## Intended install location

Copy this ZIP to the server and place it in:

```text
/srv/bili-songbot
```

Then extract it from that directory:

```bash
cd /srv/bili-songbot
unzip bili-songbot-codex-ready-pack.zip
chmod +x scripts/codex_*.sh
```

## Verify

```bash
ls -lh AGENTS.md AGENT.MD README_CODEX.md PROJECT_CONTEXT.md
bash scripts/codex_diagnose_all_live.sh
```

## No service restart required

This pack contains documentation and helper scripts only. It does not change runtime code or systemd service definitions.
