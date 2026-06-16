#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Validate transparent transition alpha channel.")
    p.add_argument("file")
    p.add_argument("--out", default="runtime/alpha_check.png")
    args = p.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-ss", "1.0", "-i", args.file, "-vf", "alphaextract", "-frames:v", "1", "-update", "1", str(out)
    ], check=True)
    print(f"已输出 Alpha 检查图：{out}")
    print("如果图片不是纯白/纯黑，并能看到转场透明形状，说明 Alpha 通道有效。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
