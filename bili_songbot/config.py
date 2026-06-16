from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .models import Song


@dataclass(slots=True)
class StreamConfig:
    output_width: int = 1280
    output_height: int = 720
    fps: int = 30
    video_bitrate: str = "4000k"
    video_maxrate: str = "4500k"
    video_bufsize: str = "9000k"
    audio_bitrate: str = "160k"
    audio_sample_rate: int = 48000
    audio_channels: int = 2
    x264_preset: str = "veryfast"
    x264_tune: str = "zerolatency"
    gop_seconds: int = 2
    chunk_seconds: float = 20.0
    transition_seconds: float = 2.15
    transition_half_seconds: float = 1.075
    ui_refresh_min_interval: float = 0.5


@dataclass(slots=True)
class BiliConfig:
    enabled: bool = False
    mode: str = "web"  # web | stdin | disabled
    room_id: int = 0
    sessdata: str = ""
    command_prefixes: list[str] = field(default_factory=lambda: ["点歌", "點歌", "song", "dg"])
    allow_direct_alias: bool = True


@dataclass(slots=True)
class QueueConfig:
    max_size: int = 10
    user_cooldown_seconds: int = 60
    recent_history_size: int = 8
    fuzzy_min_alias_len: int = 3
    fuzzy_score_cutoff: int = 90
    reject_duplicate_in_queue: bool = True


@dataclass(slots=True)
class UiConfig:
    font_path: str = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    output_path: str = "runtime/ui_overlay.png"
    show_random_preview: int = 3
    show_request_queue: int = 6
    right_top_notice: str = "歌曲的部分歌词翻译以及时轴仅供参考，目前正在升级优化中，如果发现问题请及时反馈"


@dataclass(slots=True)
class OutputConfig:
    mode: str = "local"  # local | rtmp
    rtmp_url: str = ""
    rtmp_stream_key: str = ""
    local_output: str = "runtime/local_test.flv"
    fifo_path: str = "runtime/live.ts.fifo"


@dataclass(slots=True)
class AppConfig:
    root_dir: Path
    songs_config: Path
    app_config: Path
    env_file: Path
    database_path: str = "runtime/state.db"
    log_dir: str = "logs"
    health_bind: str = "127.0.0.1"
    health_port: int = 8787
    stream: StreamConfig = field(default_factory=StreamConfig)
    bili: BiliConfig = field(default_factory=BiliConfig)
    queue: QueueConfig = field(default_factory=QueueConfig)
    ui: UiConfig = field(default_factory=UiConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    songs: list[Song] = field(default_factory=list)

    def abs_path(self, p: str | Path) -> Path:
        path = Path(p)
        return path if path.is_absolute() else self.root_dir / path


def _merge_dict(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge_dict(dst[k], v)
        else:
            dst[k] = v
    return dst


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(root_dir: str | Path | None = None) -> AppConfig:
    root = Path(root_dir or os.environ.get("BILI_SONGBOT_ROOT") or Path.cwd()).resolve()
    app_yaml = root / "config" / "app.yaml"
    songs_yaml = root / "config" / "songs.yaml"
    env_file = root / "config" / ".env"
    load_dotenv(env_file)

    raw = _load_yaml(app_yaml)
    songs_raw = _load_yaml(songs_yaml)

    stream = StreamConfig(**raw.get("stream", {}))
    bili = BiliConfig(**raw.get("bilibili", {}))
    queue = QueueConfig(**raw.get("queue", {}))
    ui = UiConfig(**raw.get("ui", {}))
    output = OutputConfig(**raw.get("output", {}))

    # .env overrides: production secrets and environment-specific values go here.
    bili.room_id = int(os.environ.get("BILI_ROOM_ID") or bili.room_id or 0)
    bili.sessdata = os.environ.get("BILI_SESSDATA", bili.sessdata or "")
    bili.enabled = os.environ.get("BILI_ENABLED", str(bili.enabled)).lower() in {"1", "true", "yes", "on"}
    bili.mode = os.environ.get("BILI_MODE", bili.mode or "web")

    output.mode = os.environ.get("OUTPUT_MODE", output.mode)
    output.rtmp_url = os.environ.get("RTMP_URL", output.rtmp_url)
    output.rtmp_stream_key = os.environ.get("RTMP_STREAM_KEY", output.rtmp_stream_key)
    output.local_output = os.environ.get("LOCAL_OUTPUT", output.local_output)

    for env_name, attr in [
        ("OUTPUT_WIDTH", "output_width"),
        ("OUTPUT_HEIGHT", "output_height"),
        ("OUTPUT_FPS", "fps"),
        ("CHUNK_SECONDS", "chunk_seconds"),
    ]:
        value = os.environ.get(env_name)
        if value:
            old = getattr(stream, attr)
            setattr(stream, attr, type(old)(value))

    stream.video_bitrate = os.environ.get("VIDEO_BITRATE", stream.video_bitrate)
    stream.video_maxrate = os.environ.get("VIDEO_MAXRATE", stream.video_maxrate)
    stream.video_bufsize = os.environ.get("VIDEO_BUFSIZE", stream.video_bufsize)
    stream.audio_bitrate = os.environ.get("AUDIO_BITRATE", stream.audio_bitrate)
    stream.x264_preset = os.environ.get("X264_PRESET", stream.x264_preset)

    if os.environ.get("TRANSITION_SECONDS"):
        stream.transition_seconds = float(os.environ["TRANSITION_SECONDS"])
        stream.transition_half_seconds = stream.transition_seconds / 2

    if os.environ.get("QUEUE_MAX_SIZE"):
        queue.max_size = int(os.environ["QUEUE_MAX_SIZE"])
    cooldown = os.environ.get("QUEUE_USER_COOLDOWN_SECONDS") or os.environ.get("USER_COOLDOWN_SECONDS")
    if cooldown:
        queue.user_cooldown_seconds = int(cooldown)

    songs = [Song.from_dict(x) for x in songs_raw.get("songs", [])]

    return AppConfig(
        root_dir=root,
        songs_config=songs_yaml,
        app_config=app_yaml,
        env_file=env_file,
        database_path=raw.get("database_path", "runtime/state.db"),
        log_dir=raw.get("log_dir", "logs"),
        health_bind=os.environ.get("HEALTH_BIND", raw.get("health_bind", "127.0.0.1")),
        health_port=int(os.environ.get("HEALTH_PORT", raw.get("health_port", 8787))),
        stream=stream,
        bili=bili,
        queue=queue,
        ui=ui,
        output=output,
        songs=songs,
    )
