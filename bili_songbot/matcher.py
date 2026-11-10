from __future__ import annotations

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
        self.command_prefixes = sorted(
            {self.normalize(x) for x in command_prefixes if self.normalize(x)},
            key=lambda x: (-len(x), x),
        )
        self.allow_direct_alias = allow_direct_alias
        self.fuzzy_min_alias_len = fuzzy_min_alias_len
        self.fuzzy_score_cutoff = fuzzy_score_cutoff
        self.alias_to_song: dict[str, Song] = {}
        self._song_id_aliases = {self.normalize(song.song_id) for song in self.songs}
        self._build_index()

    @staticmethod
    def normalize(text: str) -> str:
        text = unicodedata.normalize("NFKC", text or "").casefold()
        return "".join(
            char for char in text
            if not char.isspace()
            and not unicodedata.category(char).startswith("P")
            and unicodedata.category(char) != "Cf"
            and char not in "~<>"
        )

    def _build_index(self) -> None:
        conflicts: dict[str, list[str]] = {}
        for song in self.songs:
            aliases = set(song.aliases + [song.display_name, song.song_id])
            for alias in sorted(aliases):
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
        raw = "".join(
            char for char in unicodedata.normalize("NFKC", text or "").casefold()
            if unicodedata.category(char) != "Cf"
        ).strip()
        normalized = self.normalize(raw)
        if not normalized:
            return None

        for prefix in self.command_prefixes:
            if raw.startswith(prefix):
                rest = raw[len(prefix):]
                # Keep full English words and IDs such as songbird/song_026 intact.
                if prefix.isascii() and rest and (
                    rest[0] == "_" or (rest[0].isascii() and rest[0].isalpha())
                ):
                    continue
                rest = self.normalize(rest)
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

        if candidate.isdecimal() or (candidate.startswith("song") and candidate[4:].isdecimal()):
            return MatchResult(None, "not_found", "未找到歌曲编号")

        # Rank distinct songs, not aliases: synonyms must not hide ambiguity.
        scores: dict[str, tuple[int, Song, str]] = {}
        for alias, song in self.alias_to_song.items():
            if len(alias) < self.fuzzy_min_alias_len or alias.isdecimal():
                continue
            if alias in self._song_id_aliases:
                continue
            # Only the request may be a title fragment, not the other way round.
            # This avoids treating a whole chat sentence containing a keyword as a request.
            score = 100 if candidate in alias else fuzz.ratio(candidate, alias)
            item = (int(score), song, alias)
            previous = scores.get(song.song_id)
            if previous is None or item[0] > previous[0]:
                scores[song.song_id] = item

        ranked = sorted(scores.values(), key=lambda item: (-item[0], item[1].song_id))
        best = ranked[0] if ranked else None

        if best is None or best[0] < self.fuzzy_score_cutoff:
            return MatchResult(None, "not_found", "未找到歌曲", best[0] if best else 0)

        matches = [item for item in ranked if item[0] >= self.fuzzy_score_cutoff]
        if len(matches) > 1:
            choices = "、".join(f"{song.song_id} {song.display_name}" for _, song, _ in matches[:3])
            return MatchResult(
                None,
                "ambiguous",
                f"代号不明确，请用完整歌名或编号：{choices}",
                best[0],
                [song.display_name for _, song, _ in matches],
            )

        return MatchResult(best[1], "fuzzy", f"模糊命中：{best[2]}", best[0])
