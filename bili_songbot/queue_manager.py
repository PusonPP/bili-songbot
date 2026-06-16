from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Iterable

from .config import QueueConfig
from .matcher import SongMatcher
from .models import QueueItem, RequestResult, Song
from .storage import Storage

logger = logging.getLogger(__name__)


class QueueManager:
    def __init__(self, songs: Iterable[Song], matcher: SongMatcher, storage: Storage, cfg: QueueConfig):
        self.songs = [s for s in songs if s.enabled]
        self.songs_by_id = {s.song_id: s for s in self.songs}
        self.matcher = matcher
        self.storage = storage
        self.cfg = cfg
        self._lock = asyncio.Lock()
        self.request_queue: list[QueueItem] = []
        self.shuffle_queue: list[str] = []
        self.user_cooldowns: dict[str, float] = {}
        self.recent_history: list[str] = []
        self.changed = asyncio.Event()

    async def load(self) -> None:
        async with self._lock:
            self.request_queue = [x for x in self.storage.load_queue() if x.song_id in self.songs_by_id]
            self.user_cooldowns = self.storage.load_cooldowns()
            self.recent_history = self.storage.load_recent_history(self.cfg.recent_history_size)
            self._refill_shuffle_locked()

    async def handle_danmaku(self, uid: str, uname: str, text: str) -> RequestResult:
        now = time.time()
        match = self.matcher.match_text(text)
        if not match.song:
            return RequestResult(False, match.code, match.reason)

        async with self._lock:
            if len(self.request_queue) >= self.cfg.max_size:
                return RequestResult(False, "queue_full", "队列已满，请稍后再点", match.song.song_id, match.song.display_name)

            last = self.user_cooldowns.get(uid, 0)
            if now - last < self.cfg.user_cooldown_seconds:
                remain = int(self.cfg.user_cooldown_seconds - (now - last))
                return RequestResult(False, "cooldown", f"点歌冷却中，还需 {remain} 秒", match.song.song_id, match.song.display_name)

            if self.cfg.reject_duplicate_in_queue and any(x.song_id == match.song.song_id for x in self.request_queue):
                return RequestResult(False, "duplicate", "这首歌已经在队列中", match.song.song_id, match.song.display_name)

            item = QueueItem(song_id=match.song.song_id, uid=str(uid), uname=uname or "匿名", requested_at=now)
            self.request_queue.append(item)
            self.user_cooldowns[str(uid)] = now
            self.storage.save_queue(self.request_queue)
            self.storage.save_cooldown(str(uid), now)
            self.storage.event("INFO", "song_request", f"{uname} 点歌 {match.song.display_name}", {"uid": uid, "text": text})
            self.changed.set()
            return RequestResult(True, "accepted", "已加入点歌队列", match.song.song_id, match.song.display_name)

    async def get_next_song(self) -> Song:
        async with self._lock:
            if self.request_queue:
                item = self.request_queue.pop(0)
                self.storage.save_queue(self.request_queue)
                self.changed.set()
                return self.songs_by_id[item.song_id]

            if not self.shuffle_queue:
                self._refill_shuffle_locked()
            song_id = self.shuffle_queue.pop(0)
            if len(self.shuffle_queue) < 5:
                self._refill_shuffle_locked()
            self.changed.set()
            return self.songs_by_id[song_id]

    async def mark_played(self, song_id: str) -> None:
        async with self._lock:
            self.recent_history.insert(0, song_id)
            self.recent_history = self.recent_history[: self.cfg.recent_history_size]
            self.storage.record_history(song_id)

    async def snapshot(self) -> dict:
        async with self._lock:
            req = [
                {
                    "song_id": x.song_id,
                    "display_name": self.songs_by_id.get(x.song_id).display_name if x.song_id in self.songs_by_id else x.song_id,
                    "uid": x.uid,
                    "uname": x.uname,
                    "requested_at": x.requested_at,
                }
                for x in self.request_queue
            ]
            preview = [
                {"song_id": sid, "display_name": self.songs_by_id[sid].display_name}
                for sid in self.shuffle_queue[:8]
                if sid in self.songs_by_id
            ]
            return {"request_queue": req, "shuffle_preview": preview, "recent_history": list(self.recent_history)}

    def _refill_shuffle_locked(self) -> None:
        if not self.songs:
            raise RuntimeError("没有启用的歌曲，请检查 config/songs.yaml")
        recent = set(self.recent_history[: self.cfg.recent_history_size])
        pool = [s.song_id for s in self.songs if s.song_id not in recent]
        if len(pool) < max(3, min(5, len(self.songs))):
            pool = [s.song_id for s in self.songs]
        random.shuffle(pool)
        self.shuffle_queue.extend(pool)
