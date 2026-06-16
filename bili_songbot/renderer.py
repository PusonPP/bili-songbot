from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path

from .config import AppConfig
from .models import Song
from .pusher import StreamPusher

logger = logging.getLogger(__name__)


class FFmpegRenderer:
    def __init__(self, cfg: AppConfig, pusher: StreamPusher):
        self.cfg = cfg
        self.pusher = pusher
        self.last_error = ""
        self.last_transition_next_visible = 0.0

    def _encoding_args(self) -> list[str]:
        """Encode clean MPEG-TS chunks for the pusher.

        The final RTMP/local output is no longer produced here. UI is intentionally
        not burned into chunks; StreamPusher overlays dynamic text in one continuous
        re-encode pass so queue changes can show up without waiting for the next chunk.
        """
        s = self.cfg.stream
        gop = max(1, s.fps * s.gop_seconds)
        return [
            "-c:v",
            "libx264",
            "-preset",
            s.x264_preset,
            "-tune",
            s.x264_tune,
            "-b:v",
            s.video_bitrate,
            "-maxrate",
            s.video_maxrate,
            "-bufsize",
            s.video_bufsize,
            "-g",
            str(gop),
            "-keyint_min",
            str(gop),
            "-sc_threshold",
            "0",
            "-x264-params",
            f"keyint={gop}:min-keyint={gop}:scenecut=0:repeat-headers=1",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            s.audio_bitrate,
            "-ar",
            str(s.audio_sample_rate),
            "-ac",
            str(s.audio_channels),
            "-mpegts_flags",
            "+resend_headers",
            "-f",
            "mpegts",
            "pipe:1",
        ]

    def _base_video_filter(self) -> str:
        s = self.cfg.stream
        return f"scale={s.output_width}:{s.output_height}:force_original_aspect_ratio=decrease,pad={s.output_width}:{s.output_height}:(ow-iw)/2:(oh-ih)/2,setsar=1,setdar=16/9,fps={s.fps},format=yuv420p"

    async def render_song_chunk(self, song: Song, start: float, duration: float, ui_png: Path) -> None:
        # ui_png is kept for backward-compatible call sites. Runtime UI is now drawn by pusher.
        if duration <= 0.05:
            return
        src = self.cfg.abs_path(song.runtime_path)
        if not src.exists():
            raise FileNotFoundError(f"歌曲文件不存在：{src}")
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "warning",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(src),
            "-filter_complex",
            f"[0:v]{self._base_video_filter()}[v]",
            "-map",
            "[v]",
            "-map",
            "0:a:0?",
            "-shortest",
            *self._encoding_args(),
        ]
        await self._run_and_push(cmd, f"song_chunk {song.song_id} {start:.3f}+{duration:.3f}")

    async def render_transition(self, prev_song: Song, next_song: Song, ui_png: Path) -> None:
        """Render transition without burning UI.

        The next song is hidden below the transition until TRANSITION_REVEAL_AT. This
        avoids the visual problem where the next video appears during the LOADING stage
        before the transition door/reveal animation actually opens.
        """
        s = self.cfg.stream
        prev_src = self.cfg.abs_path(prev_song.runtime_path)
        next_src = self.cfg.abs_path(next_song.runtime_path)
        tr_src = self.cfg.abs_path(prev_song.transition_policy.transition_asset or next_song.transition_policy.transition_asset)
        if not tr_src.exists():
            logger.warning("转场文件不存在，改为硬切：%s", tr_src)
            self.last_transition_next_visible = 0.0
            return

        total = self._probe_duration(tr_src) or s.transition_seconds or s.transition_half_seconds * 2
        reveal_at = float(os.environ.get("TRANSITION_REVEAL_AT", "1.60"))
        reveal_at = max(0.0, min(reveal_at, max(0.05, total - 0.05)))
        next_visible = max(0.05, total - reveal_at)
        self.last_transition_next_visible = next_visible

        # Use previous-song tail as background, then freeze its last frame until reveal_at.
        tail = min(total, max(0.25, prev_song.duration / 3))
        prev_start = max(0.0, prev_song.duration - tail)
        prev_pad = max(0.0, total - tail)
        delay_ms = int(round(reveal_at * 1000))
        vf = self._base_video_filter()

        filter_complex = (
            f"[0:v]{vf},setpts=PTS-STARTPTS,"
            f"tpad=stop_mode=clone:stop_duration={prev_pad:.3f},"
            f"trim=duration={total:.3f},setpts=PTS-STARTPTS[prevbg];"
            f"[1:v]{vf},trim=duration={next_visible:.3f},"
            f"setpts=PTS-STARTPTS+{reveal_at:.3f}/TB[nextv];"
            f"[prevbg][nextv]overlay=0:0:enable='gte(t,{reveal_at:.3f})'[bg];"
            f"[2:v]scale={s.output_width}:{s.output_height}:flags=lanczos,"
            f"setsar=1,setdar=16/9,fps={s.fps},format=argb,"
            f"trim=duration={total:.3f},setpts=PTS-STARTPTS[tr];"
            "[bg][tr]overlay=0:0:format=auto[v];"
            f"anullsrc=channel_layout=stereo:sample_rate=48000,"
            f"atrim=duration={total:.3f}[a]"
        )
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "warning",
            "-ss",
            f"{prev_start:.3f}",
            "-t",
            f"{tail:.3f}",
            "-i",
            str(prev_src),
            "-ss",
            "0",
            "-t",
            f"{next_visible:.3f}",
            "-i",
            str(next_src),
            "-stream_loop",
            "-1",
            "-t",
            f"{total:.3f}",
            "-i",
            str(tr_src),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-shortest",
            *self._encoding_args(),
        ]
        logger.info(
            "转场时长：total=%.3fs reveal_at=%.3fs next_visible=%.3fs next=%s",
            total,
            reveal_at,
            next_visible,
            next_song.song_id,
        )
        await self._run_and_push(cmd, f"transition {prev_song.song_id}->{next_song.song_id}")

    def _probe_duration(self, path: Path) -> float | None:
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                text=True,
                capture_output=True,
                check=True,
            )
            return float(json.loads(probe.stdout)["format"]["duration"])
        except Exception:  # noqa: BLE001
            logger.exception("读取转场时长失败：%s", path)
            return None

    async def _run_and_push(self, cmd: list[str], label: str) -> None:
        logger.info("渲染片段：%s", label)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        stderr_task = asyncio.create_task(self._capture_stderr(proc, label))
        code = await self.pusher.pipe_from_process(proc)
        await stderr_task
        if code != 0:
            raise RuntimeError(f"FFmpeg 渲染失败：{label}，exit={code}")

    async def _capture_stderr(self, proc: asyncio.subprocess.Process, label: str) -> None:
        if not proc.stderr:
            return
        lines = []
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            if text:
                lines.append(text)
                logger.warning("[renderer:%s] %s", label, text)
        if lines:
            self.last_error = lines[-1]
