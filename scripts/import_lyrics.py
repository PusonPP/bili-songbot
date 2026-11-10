#!/usr/bin/env python3
"""Import an inspected local lyric manifest without changing the live catalog."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml

from bili_songbot.lyrics import bilingual_ass, read_bilingual_lrc, text_lines


def apply_reference_timing(raw: str, zh: str, reference: dict) -> tuple[str, str]:
    originals, translations = text_lines(raw), text_lines(zh)
    if len(originals) != len(translations):
        raise ValueError("Reference source/translation count differs")
    covered, events, paired = [], [], []
    previous = -1
    for group in reference["groups"]:
        numbers, timestamp = group["provided_lines"], group["start_ms"]
        if not numbers or timestamp <= previous:
            raise ValueError("Reference groups must be nonempty and chronological")
        previous = timestamp
        if any(not 1 <= n <= len(originals) for n in numbers):
            raise ValueError("Reference group index outside source text")
        covered.extend(numbers)
        events.append((timestamp, " / ".join(originals[n - 1] for n in numbers)))
        paired.append(" / ".join(translations[n - 1] for n in numbers))
    if covered != list(range(1, len(originals) + 1)):
        raise ValueError("Reference must cover every source occurrence exactly once, in order")
    events.extend((t, "") for t in reference.get("clear_ms", []))
    events.sort()
    timed = "\n".join(f"[{t // 60000:02d}:{t // 1000 % 60:02d}.{t % 1000:03d}]{s}" for t, s in events)
    return timed + "\n", "\n".join(paired) + "\n"


def correct_text(raw: str, zh: str, is_lrc: bool, patches: list[dict]) -> tuple[str, str]:
    lines = raw.lstrip("\ufeff").splitlines()
    translated = text_lines(zh)
    positions = []
    for index, line in enumerate(lines):
        if is_lrc and not re.match(r"\[\d+:\d", line.strip()):
            continue
        text = re.sub(r"^(?:\[[^]]*\])+", "", line.strip()).strip() if is_lrc else line.strip()
        if text:
            positions.append((index, text))
    if len(positions) != len(translated):
        raise ValueError("Unpaired source/translation lines")
    seen = set()
    for patch in patches:
        n = patch["line"] - 1
        if n in seen or not 0 <= n < len(positions):
            raise ValueError("Duplicate or invalid correction index")
        seen.add(n)
        pos, before = positions[n]
        if before != patch["before"]:
            raise ValueError(f"Correction source changed at lyric line {n + 1}")
        if "original" in patch:
            prefix = re.match(r"^(?:\[[^]]*\])+", lines[pos].strip()).group() if is_lrc else ""
            lines[pos] = prefix + patch["original"]
        if "translation" in patch:
            translated[n] = patch["translation"]
    return "\n".join(lines) + "\n", "\n".join(translated) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--corrections", type=Path, default=ROOT / "config/lyric_corrections.yaml")
    parser.add_argument("--reference-index", type=Path, help="Text-free, reviewed reference cue mappings")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError("Use a new release directory; existing releases are immutable")
    output.mkdir(parents=True)
    patches = yaml.safe_load(args.corrections.read_text(encoding="utf-8"))
    songs = {s["song_id"]: s for s in yaml.safe_load((ROOT / "config/songs.yaml").read_text())["songs"]}
    manifest = json.loads(args.manifest.read_text())
    references = json.loads(args.reference_index.read_text()) if args.reference_index else {}
    font = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    results = []
    for item in manifest:
        sid = item["song_id"]
        if not re.fullmatch(r"song_\d{3}", sid):
            raise ValueError("Invalid song ID")
        dst = output / sid
        dst.mkdir()
        raw_path, zh_path = ROOT / item["raw"], ROOT / item["translation"]
        raw, zh = raw_path.read_text(encoding="utf-8-sig"), zh_path.read_text(encoding="utf-8-sig")
        is_lrc = item["format"] == ".lrc"
        raw, zh = correct_text(raw, zh, is_lrc, patches.get("corrections", {}).get(sid, []))
        (dst / ("original" + item["format"])).write_text(raw, encoding="utf-8")
        (dst / "translation.zh.txt").write_text(zh, encoding="utf-8")
        row = {
            "song_id": sid, "display_name": patches.get("titles", {}).get(sid, songs[sid]["display_name"]),
            "source_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
            "translation_sha256": hashlib.sha256(zh_path.read_bytes()).hexdigest(),
            "audio_duration": item["audio_duration"], "source_format": item["format"],
            "corrections": len(patches.get("corrections", {}).get(sid, [])),
            "timing_review": "not_listened_line_by_line", "status": "untimed_keep_existing_video",
        }
        if sid in references and not is_lrc:
            provenance = references[sid]
            if provenance["source_sha256"] != row["source_sha256"] or abs(provenance["audio_duration"] - item["audio_duration"]) > .001:
                raise ValueError(f"Reference provenance mismatch: {sid}")
            if provenance.get("blocked_reason"):
                row.update(status="blocked_reference", block_reason=provenance["blocked_reason"])
            else:
                raw, zh = apply_reference_timing(raw, zh, provenance)
                (dst / "reference.lrc").write_text(raw, encoding="utf-8")
                (dst / "reference.zh.txt").write_text(zh, encoding="utf-8")
                row["timing_source"] = provenance
                is_lrc = True
        if is_lrc:
            cues = read_bilingual_lrc(raw, zh, item["audio_duration"])
            bilingual_ass(cues, row["display_name"], item["audio_duration"], font).save(str(dst / "lyrics.ass"))
            (dst / "cues.json").write_text(json.dumps([asdict(c) for c in cues], ensure_ascii=False, indent=2) + "\n")
            audio = ROOT / item["audio"]
            covers = audio.parent.parent / "covers"
            candidates = [p for p in covers.iterdir() if p.stem in {item["stem"], item["stem"] + ".bg"}]
            if len(candidates) != 1:
                raise ValueError(f"Ambiguous cover: {sid}")
            shutil.copy2(audio, dst / ("audio" + audio.suffix))
            shutil.copy2(candidates[0], dst / ("cover" + candidates[0].suffix))
            row.update(status="structural_validation_passed", cue_count=len(cues),
                       long_display_cues=[c.source_line for c in cues if c.end_ms - c.start_ms > 12000],
                       inferred_last_end=any(c.end_basis == "unverified_last_line_hold" for c in cues))
        results.append(row)
        print(sid, row["status"], flush=True)
    (output / "manifest.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
