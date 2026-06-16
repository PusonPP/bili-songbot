#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 <file> [file ...]" >&2
  exit 2
fi

for f in "$@"; do
  if [[ ! -e "$f" ]]; then
    echo "skip missing: $f" >&2
    continue
  fi
  stamp="$(date +%F_%H%M%S)"
  cp -a "$f" "${f}.bak.${stamp}"
  echo "backup: ${f}.bak.${stamp}"
done
