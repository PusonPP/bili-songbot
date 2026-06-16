#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
python3 tools/validate_alpha.py media/transition/transition_720p30_argb.mov --out runtime/alpha_check.png
