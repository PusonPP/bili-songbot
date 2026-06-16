from __future__ import annotations

import asyncio
import time
from typing import Callable, Awaitable

import psutil
import uvicorn
from fastapi import FastAPI


class HealthServer:
    def __init__(self, bind: str, port: int, status_provider: Callable[[], Awaitable[dict]]):
        self.bind = bind
        self.port = port
        self.status_provider = status_provider
        self.app = FastAPI(title="Bili Songbot Health API")
        self.started_at = time.time()
        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task | None = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        @self.app.get("/healthz")
        async def healthz():
            status = await self.status_provider()
            status.update({
                "process_uptime_seconds": round(time.time() - self.started_at, 3),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "memory_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
                "disk_percent_root": psutil.disk_usage("/").percent,
            })
            return status

        @self.app.get("/")
        async def root():
            return {"service": "bili-songbot", "health": "/healthz"}

    async def start(self) -> None:
        config = uvicorn.Config(self.app, host=self.bind, port=self.port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve())

    async def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._task:
            await self._task
