from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import pylrc
import pysubs2
from PIL import ImageFont


@dataclass(frozen=True)
class LyricCue:
    start_ms: int
    end_ms: int
    original: str
    translation: str
    source_line: int
    end_basis: str = "next_timestamp"


def text_lines(text: str) -> list[str]:
    return [line.strip() for line in text.lstrip("\ufeff").splitlines() if line.strip()]


def read_bilingual_lrc(source: str, translation: str, duration: float) -> list[LyricCue]:
    """Pair by source occurrence, not by lyric text; retain timestamped clears.

    LRC is a start-time format. Its next timestamp (including a blank cue) is
    a display boundary, NOT proof of the precise end of the sung phrase.
    """
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Audio duration must be finite and positive")
    translated = text_lines(translation)
    events: list[tuple[int, str, str, int]] = []
    offset_ms = 0
    source_index = 0
    for number, line in enumerate(source.lstrip("\ufeff").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        offset = re.fullmatch(r"\[offset:([+-]?\d+)\]", line, re.IGNORECASE)
        if offset:
            offset_ms = int(offset[1])
            continue
        if line.casefold().startswith("[offset:"):
            raise ValueError(f"Invalid LRC offset on line {number}")
        if re.fullmatch(r"\[[a-zA-Z]+:.*\]", line):
            continue
        tags = re.findall(r"\[(\d+):(\d{2})(?:\.(\d{1,3}))?\]", line)
        if not tags or any(int(seconds) >= 60 for _, seconds, _ in tags):
            raise ValueError(f"Invalid LRC timestamp on line {number}")
        parsed = pylrc.parse(line)
        if len(parsed) != len(tags):
            raise ValueError(f"Unsupported LRC syntax on line {number}")
        original = parsed[0].text.strip()
        zh = ""
        if original:
            source_index += 1
            if source_index > len(translated):
                raise ValueError("Missing translation lines")
            zh = translated[source_index - 1]
        for entry in parsed:
            events.append((round(entry.time * 1000), original, zh, source_index))
    if source_index != len(translated):
        raise ValueError(f"Translation count differs: {source_index} != {len(translated)}")
    if not events or not source_index:
        raise ValueError("No timed lyrics")
    # Match pylrc's positive-offset convention: positive means later display.
    events = sorted((t + offset_ms, jp, zh, n) for t, jp, zh, n in events)
    limit = math.floor(duration * 1000)
    starts = [row[0] for row in events]
    if len(starts) != len(set(starts)):
        raise ValueError("Ambiguous simultaneous timestamps; group the translations explicitly")
    if any(t < 0 or t >= limit for t in starts):
        raise ValueError("Timestamp outside the audio duration")
    cues = []
    for index, (start, jp, zh, number) in enumerate(events):
        if not jp:
            continue
        if index + 1 < len(events):
            end, following, _, _ = events[index + 1]
            basis = "next_timestamp" if following else "explicit_clear"
        else:
            end, basis = min(limit, start + 5000), "unverified_last_line_hold"
        cues.append(LyricCue(start, end, jp, zh, number, basis))
    validate_cues(cues, duration)
    return cues


def validate_cues(cues: list[LyricCue], duration: float) -> None:
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid audio duration")
    last_end = 0
    for cue in cues:
        if not (0 <= cue.start_ms < cue.end_ms <= math.floor(duration * 1000)):
            raise ValueError(f"Invalid cue bounds at source line {cue.source_line}")
        if cue.start_ms < last_end:
            raise ValueError(f"Overlapping cue at source line {cue.source_line}")
        if not cue.original.strip() or not cue.translation.strip():
            raise ValueError(f"Empty bilingual cue at source line {cue.source_line}")
        if cue.end_ms // 10 <= cue.start_ms // 10:
            raise ValueError("Cue is shorter than ASS centisecond precision")
        last_end = cue.end_ms


def _ass_text(text: str) -> str:
    # Treat source lyrics as text, never executable ASS override tags.
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


def _wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines, line = [], ""
    for char in text:
        if line and font.getlength(line + char) > width:
            lines.append(line.rstrip())
            line = ""
        line += char
    if line:
        lines.append(line.rstrip())
    return lines or [""]


def bilingual_ass(cues: list[LyricCue], title: str, duration: float, font_path: Path) -> pysubs2.SSAFile:
    validate_cues(cues, duration)
    subs = pysubs2.SSAFile()
    subs.info.update(PlayResX="1280", PlayResY="720", WrapStyle="2", ScaledBorderAndShadow="yes")
    subs.styles["Default"] = pysubs2.SSAStyle(
        fontname="Noto Sans CJK SC", fontsize=32, alignment=pysubs2.Alignment.MIDDLE_CENTER,
        outline=2, shadow=1, marginl=450, marginr=30,
    )
    title_font = ImageFont.truetype(str(font_path), 26)
    title_text = r"\N".join(_wrap(_ass_text(title), title_font, 744))
    subs.events.append(pysubs2.SSAEvent(
        start=0, end=math.floor(duration * 1000),
        text=r"{\an8\pos(850,120)\fs26}" + title_text,
    ))
    for cue in cues:
        for size in range(32, 17, -1):
            font = ImageFont.truetype(str(font_path), size)
            jp = _wrap(_ass_text(cue.original), font, 744)
            zh = _wrap(_ass_text(cue.translation), font, 744)
            if (len(jp) + len(zh)) * size * 1.5 <= 310:
                break
        else:
            raise ValueError(f"Lyric too long for safe display area: {cue.source_line}")
        text = (r"{\an5\pos(850,365)\fs" + str(size) + r"\1c&HFFFFFF&}"
                + r"\N".join(jp) + r"\N{\1c&HAFEFFF&}" + r"\N".join(zh))
        # Quantize both sides identically so adjacent events cannot overlap.
        subs.events.append(pysubs2.SSAEvent(
            start=cue.start_ms // 10 * 10, end=cue.end_ms // 10 * 10, text=text,
        ))
    return subs
