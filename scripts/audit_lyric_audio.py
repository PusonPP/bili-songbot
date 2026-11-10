#!/usr/bin/env python3
"""Decode supplied audio, checking PCM against FLAC STREAMINFO, without deployment."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def flac_streaminfo(path: Path) -> dict | None:
    if path.suffix.lower() != ".flac":
        return None
    with path.open("rb") as handle:
        if handle.read(4) != b"fLaC":
            raise ValueError("Missing native FLAC signature")
        header = handle.read(4)
        if len(header) != 4 or header[0] & 127 or int.from_bytes(header[1:], "big") != 34:
            raise ValueError("Invalid FLAC STREAMINFO block")
        block = handle.read(34)
    if len(block) != 34:
        raise ValueError("Truncated FLAC STREAMINFO")
    packed = int.from_bytes(block[10:18], "big")
    return {
        "sample_rate": packed >> 44, "channels": ((packed >> 41) & 7) + 1,
        "bits": ((packed >> 36) & 31) + 1,
        "samples": packed & ((1 << 36) - 1), "md5": block[18:].hex(),
    }


def inspect_audio(path: Path) -> dict:
    info = flac_streaminfo(path)
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "a:0", "-show_streams",
        "-show_entries", "stream=sample_rate,channels,duration", "-of", "json", str(path),
    ], capture_output=True, check=True, text=True)
    stream = json.loads(probe.stdout)["streams"][0]
    rate, channels = int(stream["sample_rate"]), stream["channels"]
    bits = info["bits"] if info else 16
    if bits not in (16, 24, 32):
        raise ValueError("Unsupported PCM precision for lossless MD5 validation")
    decoded = subprocess.run([
        "nice", "-n", "15", "ffmpeg", "-v", "error", "-nostdin", "-threads", "1",
        "-i", str(path), "-map", "0:a:0", "-c:a", f"pcm_s{bits}le",
        "-f", f"s{bits}le", "pipe:1",
    ], capture_output=True, timeout=300)
    stride = channels * (bits // 8)
    samples, remainder = divmod(len(decoded.stdout), stride)
    digest = hashlib.md5(decoded.stdout).hexdigest()
    with path.open("rb") as handle:
        source_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    failures = []
    if decoded.returncode or decoded.stderr:
        failures.append("decoder_reported_error")
    if remainder:
        failures.append("partial_pcm_frame")
    if info and info["samples"] and samples != info["samples"]:
        failures.append("flac_sample_count_mismatch")
    if info and info["md5"] != "0" * 32 and digest != info["md5"]:
        failures.append("flac_pcm_md5_mismatch")
    return {
        "sha256": source_hash, "header": info, "sample_rate": rate, "channels": channels,
        "decoded_samples": samples, "decoded_duration": samples / rate,
        "pcm_md5": digest, "decoder_exit": decoded.returncode,
        "decoder_error_lines": len(decoded.stderr.splitlines()),
        "failures": failures, "integrity_passed": not failures,
        "listening_review": "not_performed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new audit path")
    results = []
    for item in json.loads(args.manifest.read_text()):
        result = {"song_id": item["song_id"], **inspect_audio(Path(item["audio"]))}
        results.append(result)
        print(result["song_id"], "integrity_passed" if result["integrity_passed"] else result["failures"], flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
