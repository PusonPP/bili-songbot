"""One-shot start-live workflow."""

import json
import logging
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .browser import BiliLiveBrowser, BiliStreamInfo, BrowserAutomationError
from .config import Settings
from .cookies import CookieProvider
from .secrets import redact_text, safe_rtmp_url

LOGGER = logging.getLogger(__name__)


@dataclass
class StartResult:
    success: bool
    action: str
    reason: str
    dry_run: bool
    status: Optional[Dict[str, Any]] = None
    stream_info: Optional[Dict[str, Any]] = None
    runtime_stream_env_written: bool = False
    start_click_attempted: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class BiliLiveStarter:
    def __init__(self, settings: Settings, cookie_provider: Optional[CookieProvider] = None):
        self.settings = settings
        self.cookie_provider = cookie_provider or CookieProvider(settings.biliup_cookie_file)

    def start_live_if_needed(self, dry_run: Optional[bool] = None) -> StartResult:
        effective_dry_run = self.settings.dry_run if dry_run is None else dry_run
        start_click_attempted = False
        try:
            with BiliLiveBrowser(self.settings, self.cookie_provider) as browser:
                browser.open_dashboard()
                status = browser.status_from_current_page()
                if status.live is True:
                    stream_info = browser.extract_stream_info()
                    written = False
                    write_error = None
                    if stream_info.is_complete() and not effective_dry_run:
                        written, write_error = self._try_write_stream_env(stream_info)
                    return StartResult(
                        success=True,
                        action="already_live",
                        reason=status.reason,
                        dry_run=effective_dry_run,
                        status=status.to_dict(),
                        stream_info=stream_info.to_redacted_dict(),
                        runtime_stream_env_written=written,
                        start_click_attempted=False,
                        error=write_error,
                    )
                if status.live is None:
                    return StartResult(
                        success=False,
                        action="none",
                        reason="status_unknown_refuse_to_start",
                        dry_run=effective_dry_run,
                        status=status.to_dict(),
                        start_click_attempted=False,
                    )

                browser.ensure_live_area(self.settings.live_area_parent, self.settings.live_area_child)
                if effective_dry_run:
                    return StartResult(
                        success=True,
                        action="dry_run",
                        reason="would_click_start_live",
                        dry_run=True,
                        status=status.to_dict(),
                        start_click_attempted=False,
                    )

                browser.click_start_live()
                start_click_attempted = True
                live_status = browser.wait_until_live(timeout_seconds=90)
                stream_info = browser.extract_stream_info()
                written = False
                write_error = None
                if stream_info.is_complete():
                    written, write_error = self._try_write_stream_env(stream_info)
                    if written:
                        self._run_started_hook(stream_info)
                    reason = "started"
                else:
                    reason = "started_stream_info_missing"
                    LOGGER.error("Live started, but stream info extraction was incomplete: %s", stream_info.to_redacted_dict())
                return StartResult(
                    success=True,
                    action="started",
                    reason=reason,
                    dry_run=False,
                    status=live_status.to_dict(),
                    stream_info=stream_info.to_redacted_dict(),
                    runtime_stream_env_written=written,
                    start_click_attempted=start_click_attempted,
                    error=write_error,
                )
        except BrowserAutomationError as exc:
            return StartResult(False, "error", "browser_automation_failed", effective_dry_run, start_click_attempted=start_click_attempted, error=redact_text(exc))
        except Exception as exc:
            LOGGER.exception("start_live_if_needed failed")
            return StartResult(False, "error", "unexpected_error", effective_dry_run, start_click_attempted=start_click_attempted, error=redact_text(exc))

    def _write_stream_env(self, stream_info: BiliStreamInfo) -> bool:
        if not stream_info.rtmp_url or not stream_info.stream_key:
            return False
        path = self.settings.runtime_stream_env
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(
            [
                "BILI_RTMP_URL=%s" % _shell_env_value(stream_info.rtmp_url),
                "BILI_STREAM_KEY=%s" % _shell_env_value(stream_info.stream_key),
                "BILI_STREAM_UPDATED_AT=%s" % _shell_env_value(stream_info.detected_at),
                "",
            ]
        )
        tmp_path = Path(str(path) + ".tmp")
        tmp_path.write_text(content, encoding="utf-8")
        os.chmod(str(tmp_path), 0o600)
        os.replace(str(tmp_path), str(path))
        try:
            os.chmod(str(path), 0o600)
        except OSError:
            pass
        LOGGER.info("Runtime stream env written: %s", path)
        return True

    def _try_write_stream_env(self, stream_info: BiliStreamInfo) -> Tuple[bool, Optional[str]]:
        try:
            return self._write_stream_env(stream_info), None
        except Exception as exc:
            message = "runtime_stream_env_write_failed: %s" % redact_text(exc)
            LOGGER.error(message)
            return False, message

    def _run_started_hook(self, stream_info: BiliStreamInfo) -> None:
        if not self.settings.on_started_hook:
            return
        env = os.environ.copy()
        env.update(
            {
                "BILI_RTMP_URL": stream_info.rtmp_url or "",
                "BILI_STREAM_KEY": stream_info.stream_key or "",
                "BILI_STREAM_UPDATED_AT": stream_info.detected_at,
            }
        )
        try:
            completed = subprocess.run(
                self.settings.on_started_hook,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
        except Exception as exc:
            LOGGER.error("ON_STARTED_HOOK failed to execute: %s", redact_text(exc))
            return
        if completed.returncode != 0:
            LOGGER.error(
                "ON_STARTED_HOOK failed returncode=%s stderr=%s",
                completed.returncode,
                redact_text((completed.stderr or "")[:1000]),
            )
        elif completed.stdout:
            LOGGER.info("ON_STARTED_HOOK output: %s", redact_text(completed.stdout[:1000]))


def _shell_env_value(value: str) -> str:
    # Double-quoted env value with only shell-significant characters escaped.
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`") + '"'
