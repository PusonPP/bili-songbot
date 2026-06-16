from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from .models import QueueItem

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS queue_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_id TEXT NOT NULL,
                    uid TEXT NOT NULL,
                    uname TEXT NOT NULL,
                    requested_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cooldowns (
                    uid TEXT PRIMARY KEY,
                    last_request_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS play_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_id TEXT NOT NULL,
                    played_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runtime_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data_json TEXT NOT NULL DEFAULT '{}'
                );
                """
            )

    def load_queue(self) -> list[QueueItem]:
        with self._lock:
            rows = self._conn.execute("SELECT song_id, uid, uname, requested_at FROM queue_items ORDER BY id ASC").fetchall()
            return [QueueItem(str(r["song_id"]), str(r["uid"]), str(r["uname"]), float(r["requested_at"])) for r in rows]

    def save_queue(self, items: list[QueueItem]) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM queue_items")
            self._conn.executemany(
                "INSERT INTO queue_items(song_id, uid, uname, requested_at) VALUES(?,?,?,?)",
                [(x.song_id, x.uid, x.uname, x.requested_at) for x in items],
            )

    def load_cooldowns(self) -> dict[str, float]:
        with self._lock:
            rows = self._conn.execute("SELECT uid, last_request_at FROM cooldowns").fetchall()
            return {str(r["uid"]): float(r["last_request_at"]) for r in rows}

    def save_cooldown(self, uid: str, ts: float) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO cooldowns(uid, last_request_at) VALUES(?,?) "
                "ON CONFLICT(uid) DO UPDATE SET last_request_at=excluded.last_request_at",
                (uid, ts),
            )

    def record_history(self, song_id: str, ts: float | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO play_history(song_id, played_at) VALUES(?,?)", (song_id, ts or time.time()))

    def load_recent_history(self, limit: int) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT song_id FROM play_history ORDER BY id DESC LIMIT ?", (int(limit),)
            ).fetchall()
            return [str(r["song_id"]) for r in rows]

    def set_runtime(self, key: str, value: Any) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO runtime_state(key, value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value, ensure_ascii=False)),
            )

    def get_runtime(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute("SELECT value FROM runtime_state WHERE key=?", (key,)).fetchone()
            if not row:
                return default
            try:
                return json.loads(row["value"])
            except json.JSONDecodeError:
                return default

    def event(self, level: str, event_type: str, message: str, data: dict[str, Any] | None = None) -> None:
        logger.log(getattr(logging, level.upper(), logging.INFO), "%s: %s %s", event_type, message, data or {})
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO events(created_at, level, event_type, message, data_json) VALUES(?,?,?,?,?)",
                (time.time(), level.upper(), event_type, message, json.dumps(data or {}, ensure_ascii=False)),
            )

    def close(self) -> None:
        self._conn.close()
