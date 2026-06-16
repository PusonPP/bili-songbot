#!/usr/bin/env bash
set -euo pipefail

exec journalctl -u bili-live-keeper -f
