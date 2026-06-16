#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Probe media files with ffprobe.")
    p.add_argument("files", nargs="+")
    args = p.parse_args()
    for f in args.files:
        cp = subprocess.run([
            "ffprobe", "-hide_banner", "-v", "error", "-show_streams", "-show_format", "-print_format", "json", f
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("=" * 80)
        print(f)
        if cp.returncode != 0:
            print(cp.stderr)
            continue
        data = json.loads(cp.stdout)
        fmt = data.get("format", {})
        print("duration:", fmt.get("duration"), "bit_rate:", fmt.get("bit_rate"))
        for s in data.get("streams", []):
            print({k: s.get(k) for k in ["index", "codec_type", "codec_name", "pix_fmt", "width", "height", "r_frame_rate", "avg_frame_rate", "sample_rate", "channels", "bit_rate"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
