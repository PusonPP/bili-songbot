#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
export BILI_ENABLED=true
export BILI_MODE=stdin
export OUTPUT_MODE=local
python -m bili_songbot
