"""Configuration loading and validation."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv


DEFAULT_LIVE_CENTER_URL = (
    "https://link.bilibili.com/p/center/index?spm_id_from=333.1387.0.0"
    "#/my-room/start-live"
)


class ConfigError(RuntimeError):
    pass


@dataclass
class Settings:
    bili_room_id: Optional[str]
    bili_live_center_url: str
    biliup_cookie_file: Optional[Path]
    check_interval_seconds: int
    stop_confirm_times: int
    start_cooldown_seconds: int
    max_start_attempts_per_hour: int
    headless: bool
    dry_run: bool
    live_area_parent: str
    live_area_child: str
    runtime_stream_env: Path
    on_started_hook: Optional[str]
    save_failure_screenshot: bool
    log_level: str
    state_dir: Path
    log_dir: Path
    chromium_executable: Optional[Path]
    navigation_timeout_ms: int
    action_timeout_ms: int

    def validate_for_check(self) -> None:
        if not self.bili_room_id and not self.biliup_cookie_file:
            raise ConfigError("BILI_ROOM_ID 或 BILIUP_COOKIE_FILE 至少需要配置一个用于状态检测。")
        if self.biliup_cookie_file and not self.biliup_cookie_file.exists():
            raise ConfigError("BILIUP_COOKIE_FILE 不存在: %s" % self.biliup_cookie_file)

    def validate_for_start(self) -> None:
        if not self.biliup_cookie_file:
            raise ConfigError("start-once/daemon 需要配置 BILIUP_COOKIE_FILE。")
        if not self.biliup_cookie_file.exists():
            raise ConfigError("BILIUP_COOKIE_FILE 不存在: %s" % self.biliup_cookie_file)
        if not self.bili_live_center_url:
            raise ConfigError("BILI_LIVE_CENTER_URL 不能为空。")

    def to_redacted_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, Path):
                data[key] = str(value)
        if data.get("on_started_hook"):
            data["on_started_hook"] = "***redacted***"
        return data

    def to_json(self, redacted: bool = True) -> str:
        return json.dumps(self.to_redacted_dict() if redacted else asdict(self), ensure_ascii=False, indent=2, default=str)


def load_settings(env_file: Optional[Path] = None) -> Settings:
    if env_file:
        load_dotenv(dotenv_path=env_file, override=False)
    else:
        cwd_env = Path.cwd() / ".env"
        if cwd_env.exists():
            load_dotenv(dotenv_path=cwd_env, override=False)
        opt_env = Path("/opt/bili-live-keeper/.env")
        if opt_env.exists() and not cwd_env.exists():
            load_dotenv(dotenv_path=opt_env, override=False)

    return Settings(
        bili_room_id=_optional("BILI_ROOM_ID"),
        bili_live_center_url=_str("BILI_LIVE_CENTER_URL", DEFAULT_LIVE_CENTER_URL),
        biliup_cookie_file=_optional_path("BILIUP_COOKIE_FILE"),
        check_interval_seconds=_int("CHECK_INTERVAL_SECONDS", 30, minimum=5),
        stop_confirm_times=_int("STOP_CONFIRM_TIMES", 2, minimum=1),
        start_cooldown_seconds=_int("START_COOLDOWN_SECONDS", 300, minimum=0),
        max_start_attempts_per_hour=_int("MAX_START_ATTEMPTS_PER_HOUR", 3, minimum=1),
        headless=_bool("HEADLESS", True),
        dry_run=_bool("DRY_RUN", False),
        live_area_parent=_str("LIVE_AREA_PARENT", "电台"),
        live_area_child=_str("LIVE_AREA_CHILD", "聊天电台"),
        runtime_stream_env=Path(_str("RUNTIME_STREAM_ENV", "/opt/bili-live-keeper/runtime/stream.env")),
        on_started_hook=_optional("ON_STARTED_HOOK"),
        save_failure_screenshot=_bool("SAVE_FAILURE_SCREENSHOT", False),
        log_level=_str("LOG_LEVEL", "INFO").upper(),
        state_dir=Path(_str("STATE_DIR", "/var/lib/bili-live-keeper")),
        log_dir=Path(_str("LOG_DIR", "/var/log/bili-live-keeper")),
        chromium_executable=_optional_path("CHROMIUM_EXECUTABLE"),
        navigation_timeout_ms=_int("NAVIGATION_TIMEOUT_MS", 60000, minimum=5000),
        action_timeout_ms=_int("ACTION_TIMEOUT_MS", 15000, minimum=3000),
    )


def _optional(name: str) -> Optional[str]:
    value = os.getenv(name, "").strip()
    return value or None


def _str(name: str, default: str) -> str:
    value = os.getenv(name)
    return default if value is None or value == "" else value.strip()


def _optional_path(name: str) -> Optional[Path]:
    value = _optional(name)
    return Path(value).expanduser() if value else None


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(name: str, default: int, minimum: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError("%s 必须是整数。" % name) from exc
    if parsed < minimum:
        raise ConfigError("%s 不能小于 %s。" % (name, minimum))
    return parsed
