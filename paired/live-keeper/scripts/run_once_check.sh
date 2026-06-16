#!/usr/bin/env bash
set -euo pipefail

APP_NAME="bili-live-keeper"
APP_DIR="${APP_DIR:-/opt/${APP_NAME}}"
SERVICE_USER="bili-live-keeper"
STATE_DIR="/var/lib/${APP_NAME}"
PY="${APP_DIR}/.venv/bin/python"

if [[ ! -x "${PY}" ]]; then
  echo "Python venv not found: ${PY}" >&2
  exit 1
fi

exec sudo -u "${SERVICE_USER}" env HOME="${STATE_DIR}" XDG_CACHE_HOME="${STATE_DIR}/.cache" \
  bash -lc "cd '${APP_DIR}' && '${PY}' -m bili_live_keeper.cli check"
