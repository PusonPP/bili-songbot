"""FFmpeg keepalive pusher for third-party live sessions."""

import logging
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from dotenv import dotenv_values

from .config import Settings
from .secrets import redact_text, safe_rtmp_url

LOGGER = logging.getLogger(__name__)


class KeepalivePusher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.stop_requested = False
        self.process: Optional[subprocess.Popen] = None
        self.current_mtime: Optional[float] = None
        self.current_target: Optional[str] = None

    def run_forever(self) -> None:
        signal.signal(signal.SIGTERM, self._request_stop)
        signal.signal(signal.SIGINT, self._request_stop)
        LOGGER.info("Push keepalive supervisor started stream_env=%s", self.settings.runtime_stream_env)
        while not self.stop_requested:
            if not _env_bool("PUSH_KEEPALIVE_ENABLED", False):
                LOGGER.warning("PUSH_KEEPALIVE_ENABLED is false; pusher is idle")
                self._sleep(60)
                continue

            info = self._load_stream_info()
            if not info:
                self._stop_process()
                LOGGER.warning("Stream env is not ready yet: %s", self.settings.runtime_stream_env)
                self._sleep(10)
                continue

            target = _build_target(info["BILI_RTMP_URL"], info["BILI_STREAM_KEY"])
            mtime = self.settings.runtime_stream_env.stat().st_mtime
            if self.process and self.process.poll() is None:
                if self.current_mtime == mtime and self.current_target == target:
                    self._sleep(5)
                    continue
                LOGGER.info("Stream env changed; restarting FFmpeg pusher")
                self._stop_process()

            self.current_mtime = mtime
            self.current_target = target
            self._start_ffmpeg(target)
            self._sleep(5)

        self._stop_process()
        LOGGER.info("Push keepalive supervisor stopped")

    def _load_stream_info(self) -> Optional[Dict[str, str]]:
        path = self.settings.runtime_stream_env
        if not path.exists():
            return None
        values = dotenv_values(path)
        rtmp_url = str(values.get("BILI_RTMP_URL") or "").strip()
        stream_key = str(values.get("BILI_STREAM_KEY") or "").strip()
        if not rtmp_url or not stream_key:
            return None
        return {"BILI_RTMP_URL": rtmp_url, "BILI_STREAM_KEY": stream_key}

    def _start_ffmpeg(self, target: str) -> None:
        ffmpeg = os.getenv("PUSH_KEEPALIVE_FFMPEG", "/usr/bin/ffmpeg")
        video_size = os.getenv("PUSH_KEEPALIVE_VIDEO_SIZE", "1280x720")
        fps = os.getenv("PUSH_KEEPALIVE_FPS", "15")
        video_bitrate = os.getenv("PUSH_KEEPALIVE_VIDEO_BITRATE", "800k")
        audio_bitrate = os.getenv("PUSH_KEEPALIVE_AUDIO_BITRATE", "96k")
        gop = os.getenv("PUSH_KEEPALIVE_GOP", str(max(2, int(float(fps)) * 2)))
        bufsize = os.getenv("PUSH_KEEPALIVE_BUFSIZE", _double_bitrate(video_bitrate))
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-re",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=%s:r=%s" % (video_size, fps),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-tune",
            "zerolatency",
            "-pix_fmt",
            "yuv420p",
            "-b:v",
            video_bitrate,
            "-maxrate",
            video_bitrate,
            "-bufsize",
            bufsize,
            "-g",
            gop,
            "-c:a",
            "aac",
            "-b:a",
            audio_bitrate,
            "-ar",
            "44100",
            "-ac",
            "2",
            "-f",
            "flv",
            target,
        ]
        LOGGER.info(
            "Starting FFmpeg keepalive push target=%s video=%s fps=%s vbitrate=%s abitrate=%s",
            safe_rtmp_url(target),
            video_size,
            fps,
            video_bitrate,
            audio_bitrate,
        )
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._drain_stderr, args=(self.process,), daemon=True).start()

    def _drain_stderr(self, process: subprocess.Popen) -> None:
        if not process.stderr:
            return
        for raw_line in process.stderr:
            line = raw_line.strip()
            if not line:
                continue
            if "error" in line.lower() or "failed" in line.lower() or "server error" in line.lower():
                LOGGER.warning("FFmpeg: %s", redact_text(line[:1200]))

    def _stop_process(self) -> None:
        if not self.process:
            return
        if self.process.poll() is None:
            LOGGER.info("Stopping FFmpeg keepalive push")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None

    def _request_stop(self, signum, frame) -> None:  # type: ignore[no-untyped-def]
        LOGGER.info("Received signal %s; stopping pusher", signum)
        self.stop_requested = True

    def _sleep(self, seconds: int) -> None:
        deadline = time.time() + seconds
        while not self.stop_requested and time.time() < deadline:
            time.sleep(min(1.0, deadline - time.time()))


def _build_target(rtmp_url: str, stream_key: str) -> str:
    base = rtmp_url.strip()
    key = stream_key.strip()
    if key.startswith("?"):
        return base.rstrip("/") + "/" + key
    if key.startswith("/"):
        return base.rstrip("/") + key
    return base.rstrip("/") + "/" + key


def _double_bitrate(value: str) -> str:
    if value.endswith("k") and value[:-1].isdigit():
        return str(int(value[:-1]) * 2) + "k"
    return value


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
