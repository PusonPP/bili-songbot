#!/usr/bin/env bash
set -euo pipefail
python3 tools/probe_media.py media/source/songs/* media/source/transition/* || true
