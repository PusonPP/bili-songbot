from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

from rapidfuzz import fuzz

from .models import Song


@dataclass(slots=True)
class MatchResult:
    song: Song | None
    code: str
    reason: str
    score: int = 0
    candidates: list[str] | None = None


class SongMatcher:
    def __init__(
        self,
        songs: Iterable[Song],
        command_prefixes: list[str],
        allow_direct_alias: bool = True,
        fuzzy_min_alias_len: int = 3,
        fuzzy_score_cutoff: int = 90,
    ):
        self.songs = [s for s in songs if s.enabled]
        self.command_prefixes = [self.normalize(x) for x in command_prefixes]
        self.allow_direct_alias = allow_direct_alias
        self.fuzzy_min_alias_len = fuzzy_min_alias_len
        self.fuzzy_score_cutoff = fuzzy_score_cutoff
        self.alias_to_song: dict[str, Song] = {}
        self._build_index()

    @staticmethod
    def normalize(text: str) -> str:
        text = unicodedata.normalize("NFKC", text or "").strip().lower()
        text = re.sub(r"\s+", "", text)
        text = re.sub(r"[，。！？、,.!?;；:：\[\]（）()【】《》<>\"'`~]+", "", text)
        return text

    def _build_index(self) -> None:
        conflicts: dict[str, list[str]] = {}
        for song in self.songs:
            aliases = set(song.aliases + [song.display_name, song.song_id])
            for alias in aliases:
                key = self.normalize(alias)
                if not key:
                    continue
                if key in self.alias_to_song and self.alias_to_song[key].song_id != song.song_id:
                    conflicts.setdefault(key, [self.alias_to_song[key].song_id]).append(song.song_id)
                else:
                    self.alias_to_song[key] = song
        if conflicts:
            pairs = ", ".join(f"{k}: {v}" for k, v in conflicts.items())
            raise ValueError(f"歌曲别名冲突，请修改 config/songs.yaml：{pairs}")

    def extract_request_text(self, text: str) -> str | None:
        raw = text.strip()
        normalized = self.normalize(raw)
        if not normalized:
            return None

        for prefix in self.command_prefixes:
            if normalized.startswith(prefix):
                rest = normalized[len(prefix):]
                return rest or None

        return normalized if self.allow_direct_alias else None

    def match_text(self, text: str) -> MatchResult:
        candidate = self.extract_request_text(text)
        if not candidate:
            return MatchResult(None, "no_request", "不是点歌指令")

        if candidate in self.alias_to_song:
            return MatchResult(self.alias_to_song[candidate], "exact", "精确命中", 100)

        if len(candidate) < self.fuzzy_min_alias_len:
            return MatchResult(None, "not_found", "短代号不启用模糊匹配")

        best: tuple[int, Song, str] | None = None
        second: tuple[int, Song, str] | None = None
        for alias, song in self.alias_to_song.items():
            if len(alias) < self.fuzzy_min_alias_len:
                continue
            score = max(fuzz.ratio(candidate, alias), fuzz.partial_ratio(candidate, alias))
            item = (int(score), song, alias)
            if best is None or item[0] > best[0]:
                second = best
                best = item
            elif second is None or item[0] > second[0]:
                second = item

        if best is None or best[0] < self.fuzzy_score_cutoff:
            return MatchResult(None, "not_found", "未找到歌曲", best[0] if best else 0)

        if second and second[0] >= self.fuzzy_score_cutoff and second[1].song_id != best[1].song_id:
            return MatchResult(
                None,
                "ambiguous",
                "代号不明确",
                best[0],
                [best[1].display_name, second[1].display_name],
            )

        return MatchResult(best[1], "fuzzy", f"模糊命中：{best[2]}", best[0])
