from __future__ import annotations

import asyncio
import logging
import os
import signal
from pathlib import Path

from .config import AppConfig

logger = logging.getLogger(__name__)


def _ffescape(value: str | Path) -> str:
    """Escape a path/value for FFmpeg filter option syntax."""
    s = str(value)
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


class StreamPusher:
    """Long-lived FFmpeg process reading MPEG-TS bytes from FIFO and pushing to RTMP/local FLV.

    Renderer processes write clean MPEG-TS chunks into the same FIFO. The pusher decodes
    those chunks, overlays the current UI text from runtime text files with drawtext
    reload=1, re-encodes into one continuous H.264/AAC stream, then writes to RTMP/local FLV.

    This costs more CPU than -c copy, but it solves two production issues:
    1. UI can refresh during an already-rendered song chunk after a danmaku request.
    2. Segment timestamp/SPS/PPS discontinuities are normalized before Bilibili receives them.
    """

    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.fifo_path = cfg.abs_path(cfg.output.fifo_path)
        self.process: asyncio.subprocess.Process | None = None
        self._writer_fd: int | None = None
        self._stderr_task: asyncio.Task | None = None
        self.last_error = ""

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    def _target(self) -> str:
        if self.cfg.output.mode == "rtmp":
            base = self.cfg.output.rtmp_url.rstrip("/")
            key = self.cfg.output.rtmp_stream_key.strip()
            if not base or not key:
                raise RuntimeError("OUTPUT_MODE=rtmp 时必须设置 RTMP_URL 和 RTMP_STREAM_KEY")
            return f"{base}/{key}"
        out = self.cfg.abs_path(self.cfg.output.local_output)
        out.parent.mkdir(parents=True, exist_ok=True)
        return str(out)

    def _ui_text_paths(self) -> dict[str, Path]:
        ui_png = self.cfg.abs_path(self.cfg.ui.output_path)
        base = ui_png.with_suffix("")
        return {
            "current": base.with_name(base.name + ".current.txt"),
            "hint": base.with_name(base.name + ".hint.txt"),
            "queue": base.with_name(base.name + ".queue.txt"),
            "preview": base.with_name(base.name + ".preview.txt"),
            "notice": base.with_name(base.name + ".notice.txt"),
            "notice_0": base.with_name(base.name + ".notice.0.txt"),
            "notice_1": base.with_name(base.name + ".notice.1.txt"),
        }

    def _video_filter(self) -> str:
        s = self.cfg.stream
        font = Path(self.cfg.ui.font_path)
        if not font.is_absolute():
            font = self.cfg.abs_path(font)
        paths = self._ui_text_paths()

        w, h = s.output_width, s.output_height
        sx = w / 1280.0
        sy = h / 720.0

        def px(v: int) -> int:
            return max(1, int(round(v * sx)))

        def py(v: int) -> int:
            return max(1, int(round(v * sy)))

        # Simple, readable overlay. Keep the panel inside the left safe area and
        # avoid decorative icons/colors that make text look noisy on live video.
        panel_x = px(34)
        panel_y = py(64)
        panel_w = px(380)
        panel_h = py(574)
        pad_x = px(22)
        x = panel_x + pad_x

        y_current_title = panel_y + py(30)
        y_current = panel_y + py(70)
        y_hint_title = panel_y + py(150)
        y_hint = panel_y + py(190)
        y_queue_title = panel_y + py(286)
        y_queue = panel_y + py(326)
        y_preview_title = panel_y + py(426)
        y_preview = panel_y + py(466)

        fs_section = py(19)
        fs_current = py(23)
        fs_body = py(16)
        fs_queue = py(17)
        fs_preview = py(16)
        fs_notice = py(17)

        notice_margin = px(20)
        notice_y = py(18)

        font_arg = _ffescape(font)
        current_arg = _ffescape(paths["current"])
        hint_arg = _ffescape(paths["hint"])
        queue_arg = _ffescape(paths["queue"])
        preview_arg = _ffescape(paths["preview"])
        notice_0_arg = _ffescape(paths["notice_0"])
        notice_1_arg = _ffescape(paths["notice_1"])
        notice_alpha_0 = r"if(lt(mod(t\,60)\,28.5)\,1\,if(lt(mod(t\,60)\,30)\,(30-mod(t\,60))/1.5\,if(lt(mod(t\,60)\,58.5)\,0\,(mod(t\,60)-58.5)/1.5)))"
        notice_alpha_1 = r"if(lt(mod(t\,60)\,28.5)\,0\,if(lt(mod(t\,60)\,30)\,(mod(t\,60)-28.5)/1.5\,if(lt(mod(t\,60)\,58.5)\,1\,(60-mod(t\,60))/1.5)))"

        base = (
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,setdar=16/9,"
            f"fps={s.fps},format=yuv420p"
        )

        shapes = [
            # Main semi-transparent black panel. Drawbox has square corners, so
            # keep the design intentionally simple instead of fake neon/rounded UI.
            f"drawbox=x={panel_x+px(3)}:y={panel_y+py(3)}:w={panel_w}:h={panel_h}:color=black@0.22:t=fill",
            f"drawbox=x={panel_x}:y={panel_y}:w={panel_w}:h={panel_h}:color=black@0.58:t=fill",
            f"drawbox=x={panel_x}:y={panel_y}:w={panel_w}:h={panel_h}:color=white@0.18:t=1",
            # Current song subtle highlight, still monochrome.
            f"drawbox=x={x}:y={panel_y+py(62)}:w={panel_w-pad_x*2}:h={py(52)}:color=white@0.10:t=fill",
            f"drawbox=x={x}:y={panel_y+py(62)}:w={panel_w-pad_x*2}:h={py(52)}:color=white@0.20:t=1",
            # Thin neutral dividers.
            f"drawbox=x={x}:y={panel_y+py(134)}:w={panel_w-pad_x*2}:h={py(1)}:color=white@0.20:t=fill",
            f"drawbox=x={x}:y={panel_y+py(270)}:w={panel_w-pad_x*2}:h={py(1)}:color=white@0.18:t=fill",
            f"drawbox=x={x}:y={panel_y+py(410)}:w={panel_w-pad_x*2}:h={py(1)}:color=white@0.18:t=fill",
        ]

        texts = [
            # Section titles: plain white, no icons, no colored words.
            f"drawtext=fontfile={font_arg}:text='当前播放':x={x}:y={y_current_title}:fontsize={fs_section}:fontcolor=white@0.92:borderw=1:bordercolor=black@0.70",
            f"drawtext=fontfile={font_arg}:text='点歌提示':x={x}:y={y_hint_title}:fontsize={fs_section}:fontcolor=white@0.88:borderw=1:bordercolor=black@0.70",
            f"drawtext=fontfile={font_arg}:text='点歌队列':x={x}:y={y_queue_title}:fontsize={fs_section}:fontcolor=white@0.88:borderw=1:bordercolor=black@0.70",
            f"drawtext=fontfile={font_arg}:text='随机预告':x={x}:y={y_preview_title}:fontsize={fs_section}:fontcolor=white@0.88:borderw=1:bordercolor=black@0.70",
            # Dynamic text blocks. Smaller fonts and stronger clipping are handled
            # in ui_layer.py to prevent text from crossing the panel border.
            f"drawtext=fontfile={font_arg}:textfile={current_arg}:reload=1:x={x+px(12)}:y={y_current}:fontsize={fs_current}:fontcolor=white@0.96:line_spacing={py(5)}:borderw=1:bordercolor=black@0.75",
            f"drawtext=fontfile={font_arg}:textfile={hint_arg}:reload=1:x={x+px(12)}:y={y_hint}:fontsize={fs_body}:fontcolor=white@0.84:line_spacing={py(10)}:borderw=1:bordercolor=black@0.70",
            f"drawtext=fontfile={font_arg}:textfile={queue_arg}:reload=1:x={x+px(12)}:y={y_queue}:fontsize={fs_queue}:fontcolor=white@0.88:line_spacing={py(9)}:borderw=1:bordercolor=black@0.70",
            f"drawtext=fontfile={font_arg}:textfile={preview_arg}:reload=1:x={x+px(12)}:y={y_preview}:fontsize={fs_preview}:fontcolor=white@0.84:line_spacing={py(8)}:borderw=1:bordercolor=black@0.70",
            # Right top notices alternate every 30s with a 1.5s crossfade so
            # they do not stack over song-title text.
            f"drawtext=fontfile={font_arg}:textfile={notice_0_arg}:reload=1:x=w-tw-{notice_margin}:y={notice_y}:fontsize={fs_notice}:fontcolor=white@0.92:borderw=1:bordercolor=black@0.70:alpha='{notice_alpha_0}'",
            f"drawtext=fontfile={font_arg}:textfile={notice_1_arg}:reload=1:x=w-tw-{notice_margin}:y={notice_y}:fontsize={fs_notice}:fontcolor=white@0.92:borderw=1:bordercolor=black@0.70:alpha='{notice_alpha_1}'",
        ]

        return base + "," + ",".join(shapes + texts) + "[v]"

    def _cmd(self) -> list[str]:
        s = self.cfg.stream
        gop = max(1, s.fps * s.gop_seconds)
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "info",
            "-re",
            "-fflags",
            "+genpts+discardcorrupt",
            "-err_detect",
            "ignore_err",
            "-f",
            "mpegts",
            "-i",
            str(self.fifo_path),
            "-filter_complex",
            self._video_filter(),
            "-map",
            "[v]",
            "-map",
            "0:a:0?",
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
            "-flvflags",
            "no_duration_filesize",
            "-f",
            "flv",
            self._target(),
        ]
        return cmd

    async def start(self) -> None:
        self.fifo_path.parent.mkdir(parents=True, exist_ok=True)
        if self.fifo_path.exists():
            try:
                self.fifo_path.unlink()
            except OSError:
                pass
        os.mkfifo(self.fifo_path)
        cmd = self._cmd()
        logger.info("启动推流 FFmpeg（连续重编码 + 实时 UI）：%s", " ".join(cmd[:-1] + ["<TARGET>"]))
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        self._stderr_task = asyncio.create_task(self._log_stderr())
        # Opening write end keeps the FIFO from reaching EOF between chunk renderers.
        self._writer_fd = await asyncio.to_thread(os.open, self.fifo_path, os.O_WRONLY)

    async def _log_stderr(self) -> None:
        if not self.process or not self.process.stderr:
            return
        while True:
            line = await self.process.stderr.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            if text:
                logger.info("[pusher] %s", text)

    async def ensure_running(self) -> None:
        if self.running and self._writer_fd is not None:
            return
        await self.stop()
        await self.start()

    async def write(self, data: bytes) -> None:
        await self.ensure_running()
        assert self._writer_fd is not None
        try:
            await asyncio.to_thread(os.write, self._writer_fd, data)
        except BrokenPipeError as exc:
            # Do NOT restart only the pusher while the renderer is still writing the
            # middle of a H.264/MPEG-TS chunk. A mid-stream pusher restart starts
            # decoding without SPS/PPS and repeatedly causes:
            #   non-existing PPS / decode_slice_header error / no frame
            # Treat RTMP/FIFO BrokenPipe as a fatal stream error and let the whole
            # service restart from a clean FIFO and a fresh renderer segment.
            self.last_error = (
                "RTMP_BROKEN_PIPE_FATAL: pusher/FIFO broken; "
                "stop whole service instead of restarting pusher mid-stream"
            )
            logger.error(self.last_error)
            await self.stop()
            raise RuntimeError(self.last_error) from exc

    async def pipe_from_process(self, proc: asyncio.subprocess.Process) -> int:
        if not proc.stdout:
            raise RuntimeError("renderer stdout 未开启")
        while True:
            chunk = await proc.stdout.read(512 * 1024)
            if not chunk:
                break
            await self.write(chunk)
        return await proc.wait()

    async def stop(self) -> None:
        if self._writer_fd is not None:
            try:
                os.close(self._writer_fd)
            except OSError:
                pass
            self._writer_fd = None
        if self.process and self.process.returncode is None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await self.process.wait()
        if self._stderr_task:
            self._stderr_task.cancel()
        self.process = None
