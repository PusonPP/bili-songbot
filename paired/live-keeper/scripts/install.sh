#!/usr/bin/env bash
set -euo pipefail

APP_NAME="bili-live-keeper"
APP_DIR="/opt/${APP_NAME}"
SERVICE_USER="bili-live-keeper"
SERVICE_GROUP="bili-live-keeper"
STATE_DIR="/var/lib/${APP_NAME}"
LOG_DIR="/var/log/${APP_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SYSTEM_CHROMIUM=""

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
  if ! sudo -n true 2>/dev/null; then
    echo "当前用户没有无密码 sudo 权限。请切换到有 sudo 权限的用户后重试。" >&2
    exit 1
  fi
fi

echo "[1/9] Checking Python version"
python3 - <<'PY'
import sys
if sys.version_info < (3, 8):
    raise SystemExit("Python >= 3.8 is required")
print("Python", sys.version.split()[0])
PY

echo "[2/9] Installing system packages"
${SUDO} apt-get update
${SUDO} apt-get install -y python3 python3-venv python3-pip ca-certificates curl git

echo "[3/9] Creating service user and directories"
if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  ${SUDO} useradd --system --no-create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
fi
${SUDO} install -d -m 0755 "${APP_DIR}"
${SUDO} install -d -m 0750 -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" "${STATE_DIR}"
${SUDO} install -d -m 0750 -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" "${LOG_DIR}"

echo "[4/9] Copying project files to ${APP_DIR}"
${SUDO} cp -a "${SRC_DIR}/src" "${APP_DIR}/"
${SUDO} cp -a "${SRC_DIR}/scripts" "${APP_DIR}/"
${SUDO} cp -a "${SRC_DIR}/systemd" "${APP_DIR}/"
${SUDO} cp -a "${SRC_DIR}/requirements.txt" "${APP_DIR}/"
${SUDO} cp -a "${SRC_DIR}/pyproject.toml" "${APP_DIR}/"
${SUDO} cp -a "${SRC_DIR}/README.md" "${APP_DIR}/"
${SUDO} cp -a "${SRC_DIR}/.env.example" "${APP_DIR}/"
${SUDO} cp -a "${SRC_DIR}/.gitignore" "${APP_DIR}/"
${SUDO} install -d -m 0750 -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" "${APP_DIR}/runtime" "${APP_DIR}/logs"
${SUDO} touch "${APP_DIR}/runtime/.gitkeep" "${APP_DIR}/logs/.gitkeep"
${SUDO} chown -R root:root "${APP_DIR}/src" "${APP_DIR}/scripts" "${APP_DIR}/systemd" "${APP_DIR}/requirements.txt" "${APP_DIR}/pyproject.toml" "${APP_DIR}/README.md" "${APP_DIR}/.env.example" "${APP_DIR}/.gitignore"
${SUDO} find "${APP_DIR}/src" "${APP_DIR}/scripts" "${APP_DIR}/systemd" -type d -exec chmod 0755 {} +
${SUDO} find "${APP_DIR}/src" "${APP_DIR}/systemd" -type f -exec chmod 0644 {} +
${SUDO} find "${APP_DIR}/scripts" -type f -name "*.sh" -exec chmod 0755 {} +
${SUDO} chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${APP_DIR}/runtime" "${APP_DIR}/logs"
${SUDO} chmod 0750 "${APP_DIR}/runtime" "${APP_DIR}/logs"

echo "[5/9] Creating .env if missing"
if [[ ! -f "${APP_DIR}/.env" ]]; then
  ${SUDO} install -m 0640 -o root -g "${SERVICE_GROUP}" "${APP_DIR}/.env.example" "${APP_DIR}/.env"
else
  ${SUDO} chown root:"${SERVICE_GROUP}" "${APP_DIR}/.env"
  ${SUDO} chmod 0640 "${APP_DIR}/.env"
fi

set_env_if_blank() {
  local key="$1"
  local value="$2"
  local file="${APP_DIR}/.env"
  if ${SUDO} grep -q "^${key}=" "${file}"; then
    local current
    current="$(${SUDO} sed -n "s/^${key}=//p" "${file}" | tail -1)"
    if [[ -z "${current}" ]]; then
      ${SUDO} sed -i "s#^${key}=.*#${key}=${value}#" "${file}"
    fi
  else
    printf '%s=%s\n' "${key}" "${value}" | ${SUDO} tee -a "${file}" >/dev/null
  fi
}

if command -v chromium-browser >/dev/null 2>&1; then
  SYSTEM_CHROMIUM="$(command -v chromium-browser)"
elif command -v chromium >/dev/null 2>&1; then
  SYSTEM_CHROMIUM="$(command -v chromium)"
elif command -v google-chrome >/dev/null 2>&1; then
  SYSTEM_CHROMIUM="$(command -v google-chrome)"
fi

echo "[6/9] Creating Python virtual environment"
${SUDO} python3 -m venv "${APP_DIR}/.venv"
${SUDO} "${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip setuptools wheel
${SUDO} "${APP_DIR}/.venv/bin/python" -m pip install -r "${APP_DIR}/requirements.txt"
${SUDO} "${APP_DIR}/.venv/bin/python" -m pip install -e "${APP_DIR}"

echo "[7/9] Installing Playwright Chromium dependencies"
${SUDO} "${APP_DIR}/.venv/bin/python" -m playwright install-deps chromium || true
if ! ${SUDO} -u "${SERVICE_USER}" env HOME="${STATE_DIR}" XDG_CACHE_HOME="${STATE_DIR}/.cache" "${APP_DIR}/.venv/bin/python" -m playwright install chromium; then
  if [[ -n "${SYSTEM_CHROMIUM}" ]]; then
    set_env_if_blank "CHROMIUM_EXECUTABLE" "${SYSTEM_CHROMIUM}"
    echo "Playwright bundled Chromium install failed; using system Chromium fallback: ${SYSTEM_CHROMIUM}"
  else
    echo "Playwright Chromium install failed and no system Chromium was configured. Install Chromium or set CHROMIUM_EXECUTABLE in ${APP_DIR}/.env." >&2
    exit 1
  fi
fi
${SUDO} chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${STATE_DIR}"
${SUDO} chmod -R o-rwx "${STATE_DIR}/.cache" 2>/dev/null || true

echo "[8/9] Installing systemd service"
${SUDO} install -m 0644 "${APP_DIR}/systemd/${APP_NAME}.service" "/etc/systemd/system/${APP_NAME}.service"
if [[ -f "${APP_DIR}/systemd/${APP_NAME}-push.service" ]]; then
  ${SUDO} install -m 0644 "${APP_DIR}/systemd/${APP_NAME}-push.service" "/etc/systemd/system/${APP_NAME}-push.service"
fi
${SUDO} systemctl daemon-reload

echo "[9/9] Verifying CLI import"
cd "${APP_DIR}"
${SUDO} "${APP_DIR}/.venv/bin/python" -m compileall -q "${APP_DIR}/src"
${SUDO} "${APP_DIR}/.venv/bin/python" -m bili_live_keeper.cli print-config --redacted >/dev/null

cat <<EOF

Install finished.

Next steps:
  1. Run: sudo ${APP_DIR}/scripts/login_biliup.sh
  2. Edit: sudo nano ${APP_DIR}/.env
  3. Test: sudo -u ${SERVICE_USER} env HOME=${STATE_DIR} XDG_CACHE_HOME=${STATE_DIR}/.cache ${APP_DIR}/.venv/bin/python -m bili_live_keeper.cli check
  4. Dry-run: sudo -u ${SERVICE_USER} env HOME=${STATE_DIR} XDG_CACHE_HOME=${STATE_DIR}/.cache ${APP_DIR}/.venv/bin/python -m bili_live_keeper.cli start-once --dry-run
  5. Enable/start after successful dry-run:
     sudo systemctl enable ${APP_NAME}
     sudo systemctl start ${APP_NAME}
     # If no external OBS/FFmpeg pusher exists, also enable:
     sudo systemctl enable ${APP_NAME}-push
     sudo systemctl start ${APP_NAME}-push
EOF
