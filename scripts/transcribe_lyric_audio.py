#!/usr/bin/env python3
"""Independent local ASR evidence, never a listening certificate or deployment input."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--integrity", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--song", action="append")
    args = parser.parse_args()
    os.nice(15)
    from faster_whisper import WhisperModel
    import numpy as np

    model = WhisperModel(str(args.model), device="cpu", compute_type="int8", cpu_threads=1, num_workers=1)
    checks = {r["song_id"]: r for r in json.loads(args.integrity.read_text())}
    args.output.mkdir(parents=True, exist_ok=True)
    for item in json.loads(args.manifest.read_text()):
        sid = item["song_id"]
        if args.song and sid not in args.song:
            continue
        output = args.output / f"{sid}.json"
        if output.exists():
            continue
        with Path(item["audio"]).open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if digest != checks[sid]["sha256"]:
            raise ValueError(f"Audio changed after integrity audit: {sid}")
        if not checks[sid]["integrity_passed"]:
            print(sid, "blocked_corrupt_audio", flush=True)
            continue
        start = time.monotonic()
        decoded = subprocess.run([
            "ffmpeg", "-v", "error", "-nostdin", "-threads", "1", "-i", item["audio"],
            "-map", "0:a:0", "-filter_threads", "1", "-ac", "1", "-ar", "16000",
            "-f", "f32le", "pipe:1",
        ], capture_output=True, check=True, timeout=300)
        if decoded.stderr:
            raise ValueError(f"Decoder reported an error: {sid}")
        audio = np.frombuffer(decoded.stdout, dtype="<f4")
        segments, info = model.transcribe(
            audio, language="ja", beam_size=3, word_timestamps=True,
            condition_on_previous_text=False, vad_filter=False,
        )
        result = {
            "song_id": sid, "source_sha256": digest, "model": args.model.name,
            "language": info.language, "duration": info.duration,
            "method": "independent_asr_no_lyric_prompt", "listening_review": "not_performed",
            "segments": [asdict(segment) for segment in segments],
        }
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(sid, "segments", len(result["segments"]), "elapsed", round(time.monotonic() - start, 1), flush=True)


if __name__ == "__main__":
    main()
