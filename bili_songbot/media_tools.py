from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def ffprobe_json(path: str | Path) -> dict[str, Any]:
    cp = run([
        "ffprobe", "-hide_banner", "-v", "error", "-show_streams", "-show_format", "-print_format", "json", str(path)
    ])
    return json.loads(cp.stdout)


def media_duration(path: str | Path) -> float:
    data = ffprobe_json(path)
    fmt = data.get("format", {})
    if fmt.get("duration"):
        return float(fmt["duration"])
    for s in data.get("streams", []):
        if s.get("duration"):
            return float(s["duration"])
    return 0.0


def has_audio(path: str | Path) -> bool:
    data = ffprobe_json(path)
    return any(s.get("codec_type") == "audio" for s in data.get("streams", []))


def has_alpha(path: str | Path) -> bool:
    data = ffprobe_json(path)
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            pix = str(s.get("pix_fmt", "")).lower()
            codec = str(s.get("codec_name", "")).lower()
            if "a" in pix and pix not in {"yuv420p", "yuv422p", "yuv444p"}:
                return True
            if codec in {"qtrle", "prores_ks", "png", "webp"} and pix in {"argb", "rgba", "bgra", "yuva444p10le", "yuva420p"}:
                return True
    return False
