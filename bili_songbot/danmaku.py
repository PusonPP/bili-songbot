from __future__ import annotations

import asyncio
import http.cookies
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

from .config import AppConfig

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DanmakuEvent:
    uid: str
    uname: str
    text: str


DanmakuCallback = Callable[[DanmakuEvent], Awaitable[None]]


class BaseDanmakuListener:
    connected: bool = False

    async def run(self, callback: DanmakuCallback) -> None:
        raise NotImplementedError


class DisabledDanmakuListener(BaseDanmakuListener):
    async def run(self, callback: DanmakuCallback) -> None:
        logger.info("弹幕监听已禁用。")
        while True:
            await asyncio.sleep(3600)


class StdinDanmakuListener(BaseDanmakuListener):
    """For deployment smoke test: type a line in terminal as a danmaku message."""

    async def run(self, callback: DanmakuCallback) -> None:
        self.connected = True
        logger.info("stdin 点歌测试模式：在终端输入歌曲代号或 `点歌 代号`。")
        while True:
            raw_line = await asyncio.to_thread(input, "danmaku> ")

            # Clean terminal backspace/control characters in stdin smoke tests.
            # Real Bilibili danmaku normally does not contain these, but local
            # terminal paste/editing may produce \b or \x7f.
            buf = []
            for ch in raw_line:
                if ch in ("\\b", "\\x7f", "\b", "\x7f"):
                    if buf:
                        buf.pop()
                else:
                    buf.append(ch)

            line = "".join(buf).strip()
            if not line:
                continue
            await callback(DanmakuEvent(uid="stdin-user", uname="本地测试", text=line))


class BlivedmWebListener(BaseDanmakuListener):
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.connected = False

    async def run(self, callback: DanmakuCallback) -> None:
        try:
            import aiohttp
            import blivedm
            import blivedm.models.web as web_models
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "未安装 blivedm。请执行：pip install 'git+https://github.com/xfgryujk/blivedm.git@master'"
            ) from e

        if not self.cfg.bili.room_id:
            raise RuntimeError("BILI_ROOM_ID 未设置")

        cookies = http.cookies.SimpleCookie()
        if self.cfg.bili.sessdata:
            cookies["SESSDATA"] = self.cfg.bili.sessdata
            cookies["SESSDATA"]["domain"] = "bilibili.com"

        async with aiohttp.ClientSession() as session:
            session.cookie_jar.update_cookies(cookies)
            client = blivedm.BLiveClient(self.cfg.bili.room_id, session=session)

            outer = self

            class Handler(blivedm.BaseHandler):
                def _on_danmaku(self, client, message: web_models.DanmakuMessage):  # type: ignore[override]
                    uid = str(getattr(message, "uid", "0") or "0")
                    uname = str(getattr(message, "uname", "匿名") or "匿名")
                    msg = str(getattr(message, "msg", "") or "")
                    asyncio.create_task(callback(DanmakuEvent(uid=uid, uname=uname, text=msg)))

                def _on_heartbeat(self, client, message):  # noqa: ANN001
                    outer.connected = True

            client.set_handler(Handler())
            while True:
                try:
                    self.connected = False
                    logger.info("连接 Bilibili 直播弹幕，room_id=%s", self.cfg.bili.room_id)
                    client.start()
                    await client.join()
                except asyncio.CancelledError:
                    await client.stop_and_close()
                    raise
                except Exception:  # noqa: BLE001
                    logger.exception("弹幕连接异常，5 秒后重连")
                    try:
                        await client.stop_and_close()
                    except Exception:  # noqa: BLE001
                        pass
                    await asyncio.sleep(5)
                    client = blivedm.BLiveClient(self.cfg.bili.room_id, session=session)
                    client.set_handler(Handler())


def make_listener(cfg: AppConfig) -> BaseDanmakuListener:
    mode = (cfg.bili.mode or "disabled").lower()
    if not cfg.bili.enabled:
        return DisabledDanmakuListener()
    if mode == "stdin":
        return StdinDanmakuListener()
    if mode == "web":
        return BlivedmWebListener(cfg)
    raise ValueError(f"不支持的 BILI_MODE：{cfg.bili.mode}")
