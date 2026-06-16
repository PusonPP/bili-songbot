from __future__ import annotations

import asyncio
import logging
import signal
import time
from pathlib import Path

from .config import AppConfig
from .danmaku import DanmakuEvent, make_listener
from .health import HealthServer
from .matcher import SongMatcher
from .models import RuntimeStatus, Song
from .pusher import StreamPusher
from .queue_manager import QueueManager
from .renderer import FFmpegRenderer
from .storage import Storage
from .ui_layer import UiLayerGenerator

logger = logging.getLogger(__name__)


class SongbotApp:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.storage = Storage(cfg.abs_path(cfg.database_path))
        self.matcher = SongMatcher(
            cfg.songs,
            command_prefixes=cfg.bili.command_prefixes,
            allow_direct_alias=cfg.bili.allow_direct_alias,
            fuzzy_min_alias_len=cfg.queue.fuzzy_min_alias_len,
            fuzzy_score_cutoff=cfg.queue.fuzzy_score_cutoff,
        )
        self.queue = QueueManager(cfg.songs, self.matcher, self.storage, cfg.queue)
        self.ui = UiLayerGenerator(cfg)
        self.pusher = StreamPusher(cfg)
        self.renderer = FFmpegRenderer(cfg, self.pusher)
        self.listener = make_listener(cfg)
        self.status = RuntimeStatus()
        self._current_song: Song | None = None
        self._next_start_offset_after_transition = 0.0
        self._stop = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self.health = HealthServer(cfg.health_bind, cfg.health_port, self.get_status)

    async def start(self) -> None:
        if not self.cfg.songs:
            raise RuntimeError("config/songs.yaml 没有歌曲。请先填写 songs 配置。")
        await self.queue.load()
        initial_snapshot = await self.queue.snapshot()
        self.ui.render(None, initial_snapshot, force=True)
        self._install_signal_handlers()
        await self.pusher.start()
        await self.health.start()
        self._tasks.append(asyncio.create_task(self.listener.run(self._on_danmaku), name="danmaku-listener"))
        self._tasks.append(asyncio.create_task(self._play_loop(), name="playback-loop"))
        logger.info("服务已启动。健康检查：http://%s:%s/healthz", self.cfg.health_bind, self.cfg.health_port)
        await self._stop.wait()

    async def stop(self) -> None:
        self._stop.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.pusher.stop()
        await self.health.stop()
        self.storage.close()

    async def _on_danmaku(self, event: DanmakuEvent) -> None:
        try:
            result = await self.queue.handle_danmaku(event.uid, event.uname, event.text)
            if result.accepted:
                logger.info("点歌成功：%s -> %s", event.uname, result.display_name)
                snapshot = await self.queue.snapshot()
                self.ui.render(self._current_song, snapshot, force=True)
            elif result.code not in {"no_request"}:
                logger.info("点歌拒绝：%s text=%r code=%s message=%s", event.uname, event.text, result.code, result.message)
        except Exception:  # noqa: BLE001
            logger.exception("处理弹幕失败：%s", event)

    async def _play_loop(self) -> None:
        current: Song | None = None
        current_start_offset = 0.0
        while not self._stop.is_set():
            try:
                if current is None:
                    current = await self.queue.get_next_song()
                    current_start_offset = 0.0
                await self._play_one_song_then_transition(current, current_start_offset)
                # next song and offset are stored by _play_one_song_then_transition
                current = self._next_song_after_transition
                current_start_offset = self._next_start_offset_after_transition if current is not None else 0.0
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                self.status.ok = False
                self.status.last_error = str(e)
                self.storage.event("ERROR", "playback", str(e))

                if "RTMP_BROKEN_PIPE_FATAL" in str(e):
                    logger.critical(
                        "RTMP 推流连接已断开。停止整个服务，交给 systemd/外部守护从干净状态重启，避免 pusher 从 H.264 中间流恢复。"
                    )
                    self._stop.set()
                    return

                logger.exception("播放循环异常，3 秒后继续")
                await asyncio.sleep(3)
                current = await self.queue.get_next_song()
                current_start_offset = 0.0

    async def _play_one_song_then_transition(self, song: Song, start_offset: float) -> None:
        self.status.ok = True
        self._current_song = song
        self.status.current_song_id = song.song_id
        self.status.current_display_name = song.display_name
        self.status.current_started_at = time.time()
        self.storage.set_runtime("current_song", {"song_id": song.song_id, "started_at": self.status.current_started_at})
        await self.queue.mark_played(song.song_id)
        logger.info("开始播放：%s offset=%.3f", song.display_name, start_offset)

        half = self.cfg.stream.transition_half_seconds if song.transition_policy.enabled else 0.0
        safe_end = max(start_offset, song.duration - half) if song.duration > half * 2 else song.duration
        pos = max(0.0, start_offset)
        while pos < safe_end - 0.05:
            snapshot = await self.queue.snapshot()
            ui_path = self.ui.render(song, snapshot, force=True)
            chunk = min(self.cfg.stream.chunk_seconds, safe_end - pos)
            await self.renderer.render_song_chunk(song, pos, chunk, ui_path)
            pos += chunk

        next_song = await self.queue.get_next_song()
        self._next_song_after_transition = next_song
        self._next_start_offset_after_transition = 0.0
        if song.transition_policy.enabled and next_song.transition_policy.enabled and song.duration > half * 2 and next_song.duration > half * 2:
            snapshot = await self.queue.snapshot()
            # During transition, keep the list headed by the outgoing song.
            # The next song appears underneath the transition only after TRANSITION_REVEAL_AT.
            ui_path = self.ui.render(song, snapshot, force=True)
            await self.renderer.render_transition(song, next_song, ui_path)
            self._next_start_offset_after_transition = self.renderer.last_transition_next_visible
        else:
            logger.info("跳过转场：%s -> %s", song.song_id, next_song.song_id)
            snapshot = await self.queue.snapshot()
            self.ui.render(next_song, snapshot, force=True)

    async def get_status(self) -> dict:
        snap = await self.queue.snapshot()
        return {
            "ok": self.status.ok,
            "current_song_id": self.status.current_song_id,
            "current_display_name": self.status.current_display_name,
            "current_started_at": self.status.current_started_at,
            "queue_size": len(snap.get("request_queue", [])),
            "danmaku_connected": bool(getattr(self.listener, "connected", False)),
            "pusher_running": self.pusher.running,
            "output_mode": self.cfg.output.mode,
            "last_error": self.status.last_error or self.renderer.last_error or self.pusher.last_error,
            "snapshot": snap,
        }

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._stop.set)
            except NotImplementedError:
                pass
