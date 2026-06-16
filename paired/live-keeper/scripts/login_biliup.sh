#!/usr/bin/env bash
set -euo pipefail

APP_NAME="bili-live-keeper"
APP_DIR="${APP_DIR:-/opt/${APP_NAME}}"
SERVICE_USER="bili-live-keeper"
SERVICE_GROUP="bili-live-keeper"
STATE_DIR="/var/lib/${APP_NAME}"
COOKIE_PATH="${BILIUP_COOKIE_FILE:-${STATE_DIR}/biliup-cookies.json}"
APP_BIN_DIR="${APP_DIR}/bin"
BILIUP_RS_VERSION="${BILIUP_RS_VERSION:-v0.2.4}"

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=""
  AS_SERVICE=(runuser -u "${SERVICE_USER}" --)
else
  SUDO="sudo"
  if ! sudo -n true 2>/dev/null; then
    echo "需要 sudo 来创建受限 cookies 文件并以 ${SERVICE_USER} 写入。请使用有 sudo 权限的用户运行。" >&2
    exit 1
  fi
  AS_SERVICE=(sudo -u "${SERVICE_USER}")
fi

supports_biliup_login() {
  local bin="$1"
  [[ -x "${bin}" ]] || return 1
  "${bin}" --help 2>/dev/null | grep -Eq '(^|[[:space:]])login([[:space:]]|$)' || return 1
  "${bin}" login --help >/dev/null 2>&1 || return 1
}

install_biliup_rs() {
  local arch asset sha url tmp_dir extracted
  arch="$(uname -m)"
  case "${arch}" in
    aarch64|arm64)
      asset="biliupR-${BILIUP_RS_VERSION}-aarch64-linux.tar.xz"
      sha="d21c149d2a3ef15b3bbadb16edc453a938bbfdbf9b848e11da795cc3d79629e2"
      ;;
    *)
      echo "当前架构 ${arch} 未在脚本中内置 biliup-rs 下载项。请手动安装支持 login 的 biliup-rs 到 ${APP_BIN_DIR}/biliup。" >&2
      exit 1
      ;;
  esac
  url="https://github.com/biliup/biliup-rs/releases/download/${BILIUP_RS_VERSION}/${asset}"
  tmp_dir="$(mktemp -d)"
  echo "Installing biliup-rs ${BILIUP_RS_VERSION} for ${arch}"
  curl -fsSL -o "${tmp_dir}/${asset}" "${url}"
  echo "${sha}  ${tmp_dir}/${asset}" | sha256sum -c -
  tar -xJf "${tmp_dir}/${asset}" -C "${tmp_dir}"
  extracted="$(find "${tmp_dir}" -type f -name biliup -perm /111 | head -1)"
  if [[ -z "${extracted}" ]]; then
    echo "下载包中没有找到 biliup 可执行文件。" >&2
    rm -rf "${tmp_dir}"
    exit 1
  fi
  ${SUDO} install -d -m 0755 "${APP_BIN_DIR}"
  ${SUDO} install -m 0755 "${extracted}" "${APP_BIN_DIR}/biliup"
  rm -rf "${tmp_dir}"
}

${SUDO} install -d -m 0750 -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" "${STATE_DIR}"

if [[ -n "${BILIUP_BIN:-}" ]]; then
  :
elif supports_biliup_login "${APP_BIN_DIR}/biliup"; then
  BILIUP_BIN="${APP_BIN_DIR}/biliup"
elif command -v biliup >/dev/null 2>&1 && supports_biliup_login "$(command -v biliup)"; then
  BILIUP_BIN="$(command -v biliup)"
else
  install_biliup_rs
  BILIUP_BIN="${APP_BIN_DIR}/biliup"
fi

if ! supports_biliup_login "${BILIUP_BIN}"; then
  echo "找到的 biliup 不支持 login 子命令: ${BILIUP_BIN}" >&2
  echo "请安装 biliup-rs，或设置 BILIUP_BIN 指向支持 login 的 biliup-rs 二进制。" >&2
  exit 1
fi

echo "将运行 biliup 登录流程，不保存账号密码。"
echo "cookies 输出路径: ${COOKIE_PATH}"
echo "biliup-rs: ${BILIUP_BIN}"
echo "工作目录: ${STATE_DIR}"
echo "如果出现二维码/短信/浏览器确认，请按 biliup 提示人工完成。"

"${AS_SERVICE[@]}" env HOME="${STATE_DIR}" bash -c 'cd "$1" && exec "$2" -u "$3" login' _ "${STATE_DIR}" "${BILIUP_BIN}" "${COOKIE_PATH}"

${SUDO} chown "${SERVICE_USER}:${SERVICE_GROUP}" "${COOKIE_PATH}"
${SUDO} chmod 0600 "${COOKIE_PATH}"
if [[ -f "${STATE_DIR}/qrcode.png" ]]; then
  ${SUDO} chown "${SERVICE_USER}:${SERVICE_GROUP}" "${STATE_DIR}/qrcode.png"
  ${SUDO} chmod 0600 "${STATE_DIR}/qrcode.png"
fi

ENV_FILE="${APP_DIR}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "是否把 BILIUP_COOKIE_FILE=${COOKIE_PATH} 写入 ${ENV_FILE}? [y/N] " answer
  else
    answer="n"
  fi
  if [[ "${answer}" =~ ^[Yy]$ ]]; then
    if ${SUDO} grep -q '^BILIUP_COOKIE_FILE=' "${ENV_FILE}"; then
      ${SUDO} sed -i "s#^BILIUP_COOKIE_FILE=.*#BILIUP_COOKIE_FILE=${COOKIE_PATH}#" "${ENV_FILE}"
    else
      printf 'BILIUP_COOKIE_FILE=%s\n' "${COOKIE_PATH}" | ${SUDO} tee -a "${ENV_FILE}" >/dev/null
    fi
    ${SUDO} chown root:"${SERVICE_GROUP}" "${ENV_FILE}"
    ${SUDO} chmod 0640 "${ENV_FILE}"
  fi
fi

echo "登录完成。cookies 文件权限已限制为 600。"
echo "请确认 ${ENV_FILE} 中 BILIUP_COOKIE_FILE 指向: ${COOKIE_PATH}"
