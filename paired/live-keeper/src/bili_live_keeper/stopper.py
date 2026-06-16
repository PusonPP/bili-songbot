"""Explicit one-shot stop-live workflow."""

import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from .browser import BiliLiveBrowser, BrowserAutomationError
from .config import Settings
from .cookies import CookieProvider
from .secrets import redact_text

LOGGER = logging.getLogger(__name__)


@dataclass
class StopResult:
    success: bool
    action: str
    reason: str
    status: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class BiliLiveStopper:
    """Stops live only when explicitly invoked by CLI."""

    def __init__(self, settings: Settings, cookie_provider: Optional[CookieProvider] = None):
        self.settings = settings
        self.cookie_provider = cookie_provider or CookieProvider(settings.biliup_cookie_file)

    def stop_live_if_live(self) -> StopResult:
        try:
            with BiliLiveBrowser(self.settings, self.cookie_provider) as browser:
                browser.open_dashboard()
                status = browser.status_from_current_page()
                if status.live is False:
                    return StopResult(True, "already_stopped", status.reason, status=status.to_dict())
                if status.live is None:
                    return StopResult(False, "none", "status_unknown_refuse_to_stop", status=status.to_dict())

                if not browser.click_close_live_explicit():
                    return StopResult(False, "error", "close_live_button_not_clicked", status=status.to_dict())

                if not browser.confirm_close_live_explicit():
                    return StopResult(False, "error", "close_live_confirmation_not_clicked", status=status.to_dict())

                if not browser.wait_until_stopped(timeout_seconds=60):
                    return StopResult(False, "error", "stop_live_timeout", status=status.to_dict())

                final_status = browser.status_from_current_page()
                return StopResult(True, "stopped", "detected_start_live_button", status=final_status.to_dict())
        except BrowserAutomationError as exc:
            return StopResult(False, "error", "browser_automation_failed", error=redact_text(exc))
        except Exception as exc:
            LOGGER.exception("stop_live_if_live failed")
            return StopResult(False, "error", "unexpected_error", error=redact_text(exc))
