"""Live status detection with API, dashboard HTTP, and Playwright fallbacks."""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

from .config import Settings
from .cookies import CookieProvider
from .secrets import redact_text

LOGGER = logging.getLogger(__name__)


@dataclass
class LiveStatus:
    live: Optional[bool]
    source: str
    reason: str
    checked_at: str
    confidence: str
    detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def unknown_status(source: str, reason: str, detail: Optional[str] = None) -> LiveStatus:
    return LiveStatus(
        live=None,
        source=source,
        reason=reason,
        checked_at=utc_now(),
        confidence="low",
        detail=redact_text(detail) if detail else None,
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LiveStatusChecker:
    def __init__(self, settings: Settings, cookie_provider: Optional[CookieProvider] = None):
        self.settings = settings
        self.cookie_provider = cookie_provider or CookieProvider(settings.biliup_cookie_file)

    def check(self, allow_playwright: bool = True) -> LiveStatus:
        if self.settings.biliup_cookie_file:
            try:
                self.cookie_provider.load()
            except Exception as exc:
                LOGGER.warning("Cookie preflight failed: %s", exc)

        if self.settings.bili_room_id:
            status = self._check_room_api(self.settings.bili_room_id)
            if status.live is not None and status.confidence in {"high", "medium"}:
                return status
            LOGGER.warning("Room API status was inconclusive: %s", status.reason)

        if self.settings.biliup_cookie_file:
            status = self._check_dashboard_http()
            if status.live is not None:
                return status
            LOGGER.info("Dashboard HTTP status was inconclusive: %s", status.reason)

            if allow_playwright:
                return self._check_dashboard_playwright()

        return unknown_status("none", "no_reliable_status_source")

    def _check_room_api(self, room_id: str) -> LiveStatus:
        endpoints = [
            ("room_v1", "https://api.live.bilibili.com/room/v1/Room/get_info", {"room_id": room_id}),
            (
                "xlive_index",
                "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom",
                {"room_id": room_id},
            ),
        ]
        last_error: Optional[str] = None
        for source_name, url, params in endpoints:
            try:
                response = requests.get(url, params=params, timeout=12, headers=_default_headers())
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                last_error = "%s: %s" % (source_name, exc)
                continue
            live_status = _find_live_status(payload)
            if live_status == 1:
                return LiveStatus(True, "api", "room_live_status_1", utc_now(), "high")
            if live_status in {0, 2}:
                return LiveStatus(False, "api", "room_live_status_%s" % live_status, utc_now(), "medium")
            last_error = "%s: live_status missing in response" % source_name
        return unknown_status("api", "api_unknown", last_error)

    def _check_dashboard_http(self) -> LiveStatus:
        try:
            bundle = self.cookie_provider.load()
        except Exception as exc:
            return unknown_status("dashboard_http", "cookie_load_failed", str(exc))
        try:
            response = requests.get(
                self.settings.bili_live_center_url,
                timeout=20,
                cookies=bundle.requests_dict(),
                headers=_default_headers(),
                allow_redirects=True,
            )
        except Exception as exc:
            return unknown_status("dashboard_http", "request_failed", str(exc))
        text = response.text or ""
        if response.url and "passport.bilibili.com" in response.url:
            return unknown_status("dashboard_http", "login_required", response.url)
        if _contains_verification_text(text):
            return unknown_status("dashboard_http", "manual_verification_required")
        if "关闭直播" in text:
            return LiveStatus(True, "dashboard_http", "detected_close_live_button", utc_now(), "high")
        if "开始直播" in text:
            return LiveStatus(False, "dashboard_http", "detected_start_live_button", utc_now(), "high")
        if "服务器地址" in text and ("直播码" in text or "推流密钥" in text or "串流密钥" in text):
            return unknown_status("dashboard_http", "detected_stream_fields_without_live_button")
        if "登录" in text and ("扫码登录" in text or "请先登录" in text):
            return unknown_status("dashboard_http", "login_required")
        return unknown_status("dashboard_http", "dashboard_html_no_signal", "status_code=%s" % response.status_code)

    def _check_dashboard_playwright(self) -> LiveStatus:
        try:
            from .browser import BiliLiveBrowser

            with BiliLiveBrowser(self.settings, self.cookie_provider) as browser:
                return browser.detect_status()
        except Exception as exc:
            LOGGER.warning("Playwright status check failed: %s", exc)
            return unknown_status("playwright", "playwright_failed", str(exc))


def _default_headers() -> Dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    }


def _find_live_status(payload: Any) -> Optional[int]:
    if isinstance(payload, dict):
        for key in ("live_status", "liveStatus", "status"):
            value = payload.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
        for value in payload.values():
            found = _find_live_status(value)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_live_status(item)
            if found is not None:
                return found
    return None


def _contains_verification_text(text: str) -> bool:
    signals = ["安全验证", "验证码", "人脸验证", "短信验证", "二次验证", "验证中心", "请完成验证"]
    return any(signal in text for signal in signals)
