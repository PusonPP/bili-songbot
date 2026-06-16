#!/usr/bin/env bash
set -euo pipefail
sudo apt update
sudo apt install -y ffmpeg python3 python3-venv python3-pip fonts-noto-cjk sqlite3 jq git curl htop iotop iftop logrotate ufw
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel
pip install -r requirements.txt
pip install "git+https://github.com/xfgryujk/blivedm.git@master"
