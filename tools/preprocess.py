#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import yaml


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    p = argparse.ArgumentParser(description="Preprocess songs and transparent transition for bili-songbot.")
    p.add_argument("--root", default=".")
    p.add_argument("--songs", default="config/songs.yaml")
    p.add_argument("--only", choices=["songs", "transition", "all"], default="all")
    args = p.parse_args()
    root = Path(args.root).resolve()
    songs_yaml = root / args.songs
    data = yaml.safe_load(songs_yaml.read_text("utf-8")) or {}
    stream = (yaml.safe_load((root / "config/app.yaml").read_text("utf-8")) or {}).get("stream", {})
    w = int(stream.get("output_width", 1280))
    h = int(stream.get("output_height", 720))
    fps = int(stream.get("fps", 30))
    preset = str(stream.get("x264_preset", "veryfast"))
    audio_br = str(stream.get("audio_bitrate", "160k"))
    gop = fps * int(stream.get("gop_seconds", 2))

    if args.only in {"songs", "all"}:
        for song in data.get("songs", []):
            if not song.get("enabled", True):
                continue
            src = root / song["file_path"]
            out = root / (song.get("normalized_file_path") or f"media/normalized/{song['song_id']}_{h}p{fps}.mp4")
            out.parent.mkdir(parents=True, exist_ok=True)
            run([
                "ffmpeg", "-y", "-i", str(src),
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,setdar=16/9,fps={fps},format=yuv420p",
                "-c:v", "libx264", "-preset", preset, "-crf", "20",
                "-profile:v", "high", "-g", str(gop), "-keyint_min", str(gop), "-sc_threshold", "0",
                "-c:a", "aac", "-b:a", audio_br, "-ar", "48000", "-ac", "2",
                "-movflags", "+faststart", str(out)
            ])

    if args.only in {"transition", "all"}:
        # Transition runtime path is usually the processed output.
        # Preprocess must use the original source file when transition_policy points to the processed file.
        first = next((s for s in data.get("songs", []) if s.get("enabled", True)), None)
        if first:
            out = root / "media/transition/transition_720p30_argb.mov"
            tmp = root / "media/transition/transition_720p30_argb.tmp.mov"
            source_default = root / "media/source/transition/透明底转場.mov"
            source_default_alt = root / "media/source/transition/透明底转场.mov"

            tr = first.get("transition_policy", {}).get("transition_asset", "media/source/transition/透明底转场.mov")
            src = root / tr

            # Prefer the original uploaded transition source.
            if source_default_alt.exists():
                original_src = source_default_alt
            else:
                original_src = source_default

            # If config points to the processed output, do not use it as input.
            try:
                same_as_out = src.exists() and src.resolve() == out.resolve()
            except FileNotFoundError:
                same_as_out = False

            if (not src.exists()) or same_as_out:
                src = original_src

            if not src.exists():
                if out.exists():
                    print(f"[WARN] original transition source not found, but processed transition exists: {out}; skip transition preprocessing.")
                else:
                    raise FileNotFoundError(f"transition source not found: {src}")
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                if tmp.exists():
                    tmp.unlink()
                run([
                    "ffmpeg", "-y", "-i", str(src),
                    "-vf", f"fps={fps},scale={w}:{h}:flags=lanczos,setsar=1,setdar=16/9,format=argb",
                    "-c:v", "qtrle", "-pix_fmt", "argb", str(tmp)
                ])
                tmp.replace(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
