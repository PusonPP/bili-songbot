#!/usr/bin/env python3
"""Produce per-line audio evidence; never turn ASR into approved subtitle timing."""
from __future__ import annotations

import argparse
import csv
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml

from bili_songbot.lyrics import read_bilingual_lrc, text_lines
from scripts.import_lyrics import apply_reference_timing, correct_text


def normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


def match_lines(lines: list[str], segments: list[dict]) -> list[dict]:
    source, words = "", []
    for segment in segments:
        words.extend(segment.get("words", []))
    spoken, word_indices = "", []
    for index, word in enumerate(words):
        normalized = normalize(word["word"])
        spoken += normalized
        word_indices.extend([index] * len(normalized))
    ranges = []
    for line in lines:
        start = len(source)
        source += normalize(line)
        ranges.append((start, len(source)))
    pairs = {}
    for block in SequenceMatcher(None, source, spoken, autojunk=False).get_matching_blocks():
        for offset in range(block.size):
            pairs[block.a + offset] = block.b + offset
    results = []
    for start, end in ranges:
        matched = [i for i in range(start, end) if i in pairs]
        coverage = len(matched) / (end - start) if end > start else 0
        result = {"text_coverage": round(coverage, 3), "anchor_candidate": False}
        if matched:
            first, last = words[word_indices[pairs[matched[0]]]], words[word_indices[pairs[matched[-1]]]]
            matched_words = {word_indices[pairs[i]] for i in matched}
            confidence = sum(words[i]["probability"] for i in matched_words) / len(matched_words)
            result.update(asr_start_ms=round(first["start"] * 1000),
                          asr_end_ms=round(last["end"] * 1000), mean_probability=round(confidence, 3))
            # Even a high-coverage anchor remains pending listening; short phrases
            # and unanchored line edges are especially easy false matches in songs.
            result["anchor_candidate"] = bool(
                end - start >= 6 and coverage >= .85 and confidence >= .75
                and matched[0] == start and matched[-1] == end - 1
                and last["end"] > first["start"]
            )
        results.append(result)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--asr", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new review directory")
    args.output.mkdir(parents=True)
    patches = yaml.safe_load((ROOT / "config/lyric_corrections.yaml").read_text())
    refs = json.loads((ROOT / "config/lyric_reference_timings.json").read_text())
    summaries = []
    for item in json.loads(args.manifest.read_text()):
        sid = item["song_id"]
        raw, zh = correct_text(Path(item["raw"]).read_text(), Path(item["translation"]).read_text(),
                               item["format"] == ".lrc", patches.get("corrections", {}).get(sid, []))
        timed = item["format"] == ".lrc"
        if not timed and sid in refs and not refs[sid].get("blocked_reason"):
            raw, zh = apply_reference_timing(raw, zh, refs[sid])
            timed = True
        if timed:
            cues = read_bilingual_lrc(raw, zh, item["audio_duration"])
            lines, translated = [c.original for c in cues], [c.translation for c in cues]
        else:
            lines, translated = text_lines(raw), text_lines(zh)
            cues = []
        asr = args.asr / f"{sid}.json"
        evidence = json.loads(asr.read_text()) if asr.exists() else None
        if evidence:
            with Path(item["audio"]).open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            if evidence["source_sha256"] != digest:
                raise ValueError(f"ASR audio provenance mismatch: {sid}")
        alignment = match_lines(lines, evidence["segments"] if evidence else [])
        rows = []
        for index, (original, translation, anchor) in enumerate(zip(lines, translated, alignment), 1):
            row = {"line": index, "original": original, "translation": translation,
                   "listening_review": "not_performed", "approved_for_retiming": False, **anchor}
            if cues:
                cue = cues[index - 1]
                row.update(display_start_ms=cue.start_ms, display_end_ms=cue.end_ms, end_basis=cue.end_basis)
                if anchor["anchor_candidate"]:
                    row["start_difference_ms"] = anchor["asr_start_ms"] - cue.start_ms
                    row["timing_disagreement"] = abs(row["start_difference_ms"]) > 750
            rows.append(row)
        (args.output / f"{sid}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        fields = list(dict.fromkeys(k for row in rows for k in row))
        with (args.output / f"{sid}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        summaries.append({
            "song_id": sid, "rows": len(rows), "asr_available": bool(evidence),
            "has_existing_timestamps": timed,
            "anchor_candidates": sum(r["anchor_candidate"] for r in rows),
            "timing_comparisons": sum("start_difference_ms" in r for r in rows),
            "timing_disagreements": sum(r.get("timing_disagreement", False) for r in rows),
            "listening_passed": False, "retiming_approved": False,
            "status": "deferred_by_user" if sid == "song_030" else "needs_listening",
        })
    (args.output / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    print("songs", len(summaries), "rows", sum(r["rows"] for r in summaries), "listening_passed", 0)


if __name__ == "__main__":
    main()
