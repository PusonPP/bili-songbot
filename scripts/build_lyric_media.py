#!/usr/bin/env python3
"""Build clean still-image masters from imported originals; never alter live YAML."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_lyric_audio import inspect_audio


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("--song", help="Only build this song")
    args = parser.parse_args()
    for item in json.loads((args.release / "manifest.json").read_text()):
        if item["status"] != "structural_validation_passed" or (args.song and item["song_id"] != args.song):
            continue
        folder = args.release / item["song_id"]
        final, partial = folder / "clean.mp4", folder / "clean.partial.mp4"
        if final.exists():
            print(item["song_id"], "already_built", flush=True)
            continue
        if partial.exists():
            raise ValueError(f"Incomplete previous build: {partial}")
        audio, cover = next(folder.glob("audio.*")), next(folder.glob("cover.*"))
        integrity = inspect_audio(audio)
        if not integrity["integrity_passed"]:
            raise ValueError(f"Source audio failed integrity validation: {item['song_id']}")
        if abs(integrity["decoded_duration"] - item["audio_duration"]) > .08:
            raise ValueError(f"Source PCM duration differs from manifest: {item['song_id']}")
        # Still masters use 2 fps; the live renderer expands to 30 fps BEFORE ASS.
        # Pad video to the next half-second, but never pad/trim the source audio.
        video_duration = math.ceil(item["audio_duration"] * 2) / 2
        cmd = [
            "nice", "-n", "15", "ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-xerror", "-n",
            "-filter_threads", "1", "-loop", "1", "-framerate", "2", "-i", str(cover),
            "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-map_metadata", "-1",
            "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
            "setsar=1,drawbox=color=black@0.40:t=fill",
            "-t", str(video_duration), "-c:v", "libx264", "-threads", "1", "-preset", "veryfast",
            "-tune", "stillimage", "-crf", "20", "-pix_fmt", "yuv420p", "-g", "4",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(partial),
        ]
        subprocess.run(cmd, check=True, timeout=max(180, item["audio_duration"] * 2))
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(partial)],
                               text=True, capture_output=True, check=True)
        streams = json.loads(probe.stdout)["streams"]
        a = next(s for s in streams if s["codec_type"] == "audio")
        v = next(s for s in streams if s["codec_type"] == "video")
        if abs(float(a["duration"]) - item["audio_duration"]) > .08 or (v["width"], v["height"]) != (1280, 720):
            raise ValueError(f"Generated media failed validation: {item['song_id']}")
        partial.rename(final)
        print(item["song_id"], "built", flush=True)


if __name__ == "__main__":
    main()
