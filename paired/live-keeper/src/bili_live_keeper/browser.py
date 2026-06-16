"""Playwright automation for the Bilibili live dashboard."""

import logging
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Pattern, Sequence, Union

from .config import Settings
from .cookies import CookieProvider
from .secrets import redact_text, safe_rtmp_url
from .status import LiveStatus, utc_now

LOGGER = logging.getLogger(__name__)

TextNeedle = Union[str, Pattern[str]]


class BrowserAutomationError(RuntimeError):
    pass


class LoginRequiredError(BrowserAutomationError):
    pass


class ManualVerificationRequiredError(BrowserAutomationError):
    pass


class UnsafeClickRefusedError(BrowserAutomationError):
    pass


@dataclass
class BiliStreamInfo:
    rtmp_url: Optional[str]
    stream_key: Optional[str]
    detected_at: str

    def is_complete(self) -> bool:
        return bool(self.rtmp_url and self.stream_key)

    def to_redacted_dict(self) -> Dict[str, Any]:
        return {
            "rtmp_url": safe_rtmp_url(self.rtmp_url or ""),
            "stream_key": "***redacted***" if self.stream_key else None,
            "detected_at": self.detected_at,
        }


class BiliLiveBrowser:
    def __init__(self, settings: Settings, cookie_provider: Optional[CookieProvider] = None):
        self.settings = settings
        self.cookie_provider = cookie_provider or CookieProvider(settings.biliup_cookie_file)
        self._playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self) -> "BiliLiveBrowser":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.close()

    def start(self) -> None:
        if self.browser:
            return
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - depends on runtime install
            raise BrowserAutomationError("Playwright 未安装或无法导入，请先运行安装脚本。") from exc

        self._playwright = sync_playwright().start()
        executable_path = str(self.settings.chromium_executable) if self.settings.chromium_executable else None
        launch_options: Dict[str, Any] = {
            "headless": self.settings.headless,
            "args": [
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
            ],
        }
        if executable_path:
            launch_options["executable_path"] = executable_path
        if os.geteuid() == 0:
            launch_options["args"].append("--no-sandbox")
        self.browser = self._playwright.chromium.launch(**launch_options)
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 1000},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        bundle = self.cookie_provider.load()
        playwright_cookies = bundle.playwright_cookies()
        if not playwright_cookies:
            raise BrowserAutomationError("cookies 文件没有可用于 Playwright 的有效 cookie。")
        self.context.add_cookies(playwright_cookies)
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.settings.action_timeout_ms)
        self.page.set_default_navigation_timeout(self.settings.navigation_timeout_ms)

    def close(self) -> None:
        for obj in (self.context, self.browser):
            try:
                if obj:
                    obj.close()
            except Exception:
                pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def open_dashboard(self) -> None:
        self._require_page()
        LOGGER.info("Opening live center dashboard")
        self.page.goto(self.settings.bili_live_center_url, wait_until="domcontentloaded")
        self._wait_for_dashboard_signal()
        self._raise_if_login_or_verification()

    def detect_status(self) -> LiveStatus:
        self.open_dashboard()
        return self.status_from_current_page()

    def status_from_current_page(self) -> LiveStatus:
        self._require_page()
        self._raise_if_login_or_verification()
        if self._visible_text_button(["关闭直播"]):
            return LiveStatus(True, "playwright", "detected_close_live_button", utc_now(), "high")
        if self._visible_text_button(["开始直播"]):
            return LiveStatus(False, "playwright", "detected_start_live_button", utc_now(), "high")
        text = self.body_text()
        if "服务器地址" in text and ("直播码" in text or "推流密钥" in text or "串流密钥" in text):
            return LiveStatus(None, "playwright", "detected_stream_fields_without_live_button", utc_now(), "low")
        return LiveStatus(None, "playwright", "unknown", utc_now(), "low", detail=self._safe_page_excerpt())

    def ensure_live_area(self, parent: str, child: str) -> bool:
        self._require_page()
        if self._wait_until(lambda: self._has_current_target_area(parent, child), timeout_seconds=8):
            LOGGER.info("Live area already appears to be %s / %s", parent, child)
            return True

        if not self._click_any_text(["修改分区", "请选择直播分区", "选择分区"], last=True):
            self._save_failure_diagnostics("area_opener_not_found")
            raise BrowserAutomationError("找不到“修改分区”或“请选择直播分区”，无法选择直播分区。")

        if self._wait_until(lambda: self._has_current_target_area(parent, child), timeout_seconds=2):
            LOGGER.info("Live area already confirmed as %s / %s after area control click", parent, child)
            self._dismiss_transient_dialog()
            return True

        if not self._wait_for_any_text(["直播分类", "最近选择"], timeout_seconds=15):
            if self._has_current_target_area(parent, child):
                LOGGER.info("Live area already confirmed as %s / %s without area dialog", parent, child)
                self._dismiss_transient_dialog()
                return True
            self._save_failure_diagnostics("area_dialog_not_found")
            raise BrowserAutomationError("点击分区入口后没有检测到直播分类弹窗。")

        target_pattern = re.compile(re.escape(parent) + r"\s*[·/|｜-]\s*" + re.escape(child))
        selected_combined = self._click_text_pattern(target_pattern, last=True, allow_noop=False)
        if not selected_combined:
            self._click_any_text([parent], last=True, allow_noop=True)

            search = self._first_visible_locator(
                [
                    self.page.get_by_placeholder(re.compile("开播品类|快速搜索|搜索")),
                ]
            )
            if search:
                try:
                    search.fill(child, timeout=3000)
                    time.sleep(0.5)
                except Exception:
                    pass

            if not self._click_any_text([child], last=True, allow_noop=False):
                self._save_failure_diagnostics("area_child_not_found")
                raise BrowserAutomationError("找不到二级分区“%s”，停止开播。" % child)

        if not self._click_any_text(["确定", "确认"], last=True):
            if self._has_current_target_area(parent, child):
                LOGGER.info("Live area already confirmed as %s / %s without dialog confirmation", parent, child)
                self._dismiss_transient_dialog()
                return True
            self._save_failure_diagnostics("area_confirm_not_found")
            raise BrowserAutomationError("找不到分区弹窗的“确定/确认”按钮，停止开播。")

        if not self._wait_until(lambda: self._has_current_target_area(parent, child), timeout_seconds=15):
            self._save_failure_diagnostics("area_confirm_failed")
            raise BrowserAutomationError("选择分区后没有确认看到“%s · %s”。" % (parent, child))
        LOGGER.info("Live area confirmed as %s / %s", parent, child)
        self._dismiss_transient_dialog()
        return True

    def click_start_live(self) -> None:
        self._require_page()
        if self._visible_text_button(["关闭直播"]):
            raise UnsafeClickRefusedError("页面已经显示“关闭直播”，拒绝执行任何开播点击。")
        clicked = self._click_any_button(["开始直播"], forbidden_texts=["关闭直播"], require_enabled=True)
        if not clicked:
            self._save_failure_diagnostics("start_button_not_found")
            raise BrowserAutomationError("找不到可点击的“开始直播”按钮。")
        LOGGER.info("Clicked start live button")

    def click_close_live_explicit(self) -> bool:
        self._require_page()
        if self._visible_text_button(["开始直播"]) and not self._visible_text_button(["关闭直播"]):
            LOGGER.info("Page already shows start-live button; no close-live click needed")
            return False
        clicked = self._click_any_button(["关闭直播"], forbidden_texts=["开始直播"], require_enabled=True)
        if clicked:
            LOGGER.info("Clicked close live button by explicit stop command")
        else:
            self._save_failure_diagnostics("close_button_not_found")
        return clicked

    def confirm_close_live_explicit(self) -> bool:
        self._require_page()
        deadline = time.time() + 20
        confirm_texts = ["确定", "确认", "确认关闭", "停止直播", "关闭直播"]
        while time.time() < deadline:
            for text in confirm_texts:
                locators = [
                    self.page.get_by_role("button", name=re.compile(r"^\s*" + re.escape(text) + r"\s*$")),
                    self.page.locator("button").filter(has_text=text),
                    self.page.locator("[role=button]").filter(has_text=text),
                ]
                for locator in locators:
                    if self._click_locator(locator, last=True, forbidden_texts=["开始直播"], require_enabled=True):
                        LOGGER.info("Clicked close live confirmation")
                        return True
            if self._visible_text_button(["开始直播"]):
                return True
            time.sleep(0.5)
        self._save_failure_diagnostics("close_confirm_not_found")
        return False

    def wait_until_stopped(self, timeout_seconds: int = 60) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                self.page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass
            status = self.status_from_current_page()
            if status.live is False:
                return True
            time.sleep(1.0)
        self._save_failure_diagnostics("stop_live_timeout")
        return False

    def wait_until_live(self, timeout_seconds: int = 60) -> LiveStatus:
        deadline = time.time() + timeout_seconds
        last_status = LiveStatus(None, "playwright", "not_checked", utc_now(), "low")
        while time.time() < deadline:
            try:
                self.page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass
            last_status = self.status_from_current_page()
            if last_status.live is True:
                return last_status
            time.sleep(1.0)
        self._save_failure_diagnostics("start_live_timeout")
        raise BrowserAutomationError("点击开始直播后未在 %s 秒内进入“关闭直播”状态。" % timeout_seconds)

    def extract_stream_info(self) -> BiliStreamInfo:
        self._require_page()
        values = self._collect_input_values()
        rtmp_url = None
        stream_key = None
        for value in values:
            if value.startswith(("rtmp://", "rtmps://")) and not rtmp_url:
                rtmp_url = value
            if _looks_like_stream_key(value) and not stream_key:
                stream_key = value
        if not stream_key:
            text = self.page.content()
            match = re.search(r"(\?streamname=[^\"'<>\s]+)", text)
            if match:
                stream_key = match.group(1)
        info = BiliStreamInfo(rtmp_url=rtmp_url, stream_key=stream_key, detected_at=utc_now())
        if info.rtmp_url:
            LOGGER.info("RTMP url detected: %s", safe_rtmp_url(info.rtmp_url))
        if info.stream_key:
            LOGGER.info("Stream key detected: ***redacted***")
        return info

    def body_text(self) -> str:
        self._require_page()
        try:
            return self.page.locator("body").inner_text(timeout=3000)
        except Exception:
            try:
                return self.page.content()
            except Exception:
                return ""

    def _dismiss_transient_dialog(self) -> None:
        try:
            self.page.keyboard.press("Escape", timeout=1000)
            time.sleep(0.3)
        except Exception:
            pass

    def _require_page(self) -> None:
        if not self.page:
            raise BrowserAutomationError("Playwright page 尚未初始化。")

    def _wait_for_dashboard_signal(self) -> None:
        try:
            self.page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        self._wait_for_any_text(
            [
                "开播设置",
                "开播操作",
                "开始直播",
                "关闭直播",
                "服务器地址",
                "直播码",
                "串流密钥",
                "请先登录",
                "扫码登录",
                "安全验证",
            ],
            timeout_seconds=45,
            raise_on_timeout=False,
        )

    def _raise_if_login_or_verification(self) -> None:
        text = self.body_text()
        url = self.page.url if self.page else ""
        verification_signals = ["安全验证", "验证码", "人脸验证", "短信验证", "二次验证", "请完成验证"]
        if any(signal in text for signal in verification_signals):
            self._save_failure_diagnostics("manual_verification_required")
            raise ManualVerificationRequiredError("页面触发验证码/人脸/短信/二次验证，已停止自动操作，请人工处理。")
        if "passport.bilibili.com" in url or ("扫码登录" in text and "登录" in text) or "请先登录" in text:
            self._save_failure_diagnostics("login_required")
            raise LoginRequiredError("Bilibili 后台未登录，请重新执行 biliup 登录并更新 BILIUP_COOKIE_FILE。")

    def _visible_text_button(self, texts: Sequence[str]) -> bool:
        for text in texts:
            for locator in self._button_locators(text):
                if self._has_visible(locator):
                    return True
        return False

    def _click_any_button(
        self,
        texts: Sequence[str],
        forbidden_texts: Optional[Sequence[str]] = None,
        require_enabled: bool = True,
    ) -> bool:
        for text in texts:
            for locator in self._button_locators(text):
                if self._click_locator(locator, forbidden_texts=forbidden_texts, require_enabled=require_enabled):
                    return True
        return False

    def _click_any_text(
        self,
        texts: Sequence[str],
        last: bool = False,
        allow_noop: bool = False,
    ) -> bool:
        for text in texts:
            locators = [
                self.page.get_by_role("button", name=re.compile(r"^\s*" + re.escape(text) + r"\s*$")),
                self.page.get_by_text(text, exact=True),
                self.page.locator("[role=button]").filter(has_text=text),
                self.page.locator("button").filter(has_text=text),
            ]
            for locator in locators:
                if self._click_locator(locator, last=last, forbidden_texts=["关闭直播"]):
                    return True
        return allow_noop

    def _click_text_pattern(self, pattern: Pattern[str], last: bool = False, allow_noop: bool = False) -> bool:
        locators = [
            self.page.get_by_text(pattern),
            self.page.locator("[role=button]").filter(has_text=pattern),
            self.page.locator("button").filter(has_text=pattern),
        ]
        for locator in locators:
            if self._click_locator(locator, last=last, forbidden_texts=["关闭直播"]):
                return True
        return allow_noop

    def _click_locator(
        self,
        locator: Any,
        last: bool = False,
        forbidden_texts: Optional[Sequence[str]] = None,
        require_enabled: bool = False,
    ) -> bool:
        forbidden_texts = forbidden_texts or []
        try:
            count = locator.count()
        except Exception:
            return False
        indexes = list(range(min(count, 20)))
        if last:
            indexes = list(reversed(indexes))
        for index in indexes:
            candidate = locator.nth(index)
            try:
                if not candidate.is_visible(timeout=800):
                    continue
                if require_enabled and not candidate.is_enabled(timeout=800):
                    continue
                text = _locator_text(candidate)
                if any(forbidden in text for forbidden in forbidden_texts):
                    raise UnsafeClickRefusedError("拒绝点击包含禁用文本的元素: %s" % forbidden_texts)
                candidate.click(timeout=self.settings.action_timeout_ms)
                return True
            except UnsafeClickRefusedError:
                raise
            except Exception:
                continue
        return False

    def _button_locators(self, text: str) -> List[Any]:
        escaped = re.escape(text)
        return [
            self.page.get_by_role("button", name=re.compile(r"^\s*" + escaped + r"\s*$")),
            self.page.locator("button").filter(has_text=text),
            self.page.locator("[role=button]").filter(has_text=text),
            self.page.get_by_text(text, exact=True),
        ]

    def _has_visible(self, locator: Any) -> bool:
        try:
            count = min(locator.count(), 20)
        except Exception:
            return False
        for index in range(count):
            try:
                if locator.nth(index).is_visible(timeout=500):
                    return True
            except Exception:
                continue
        return False

    def _first_visible_locator(self, locators: Iterable[Any]) -> Optional[Any]:
        for locator in locators:
            try:
                count = min(locator.count(), 10)
            except Exception:
                continue
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    if candidate.is_visible(timeout=500):
                        return candidate
                except Exception:
                    continue
        return None

    def _wait_for_any_text(
        self,
        texts: Sequence[str],
        timeout_seconds: int,
        raise_on_timeout: bool = True,
    ) -> bool:
        def has_text() -> bool:
            body = self.body_text()
            return any(text in body for text in texts)

        ok = self._wait_until(has_text, timeout_seconds)
        if not ok and raise_on_timeout:
            raise BrowserAutomationError("等待页面文本超时: %s" % ", ".join(texts))
        return ok

    def _wait_until(self, predicate, timeout_seconds: int) -> bool:  # type: ignore[no-untyped-def]
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                if predicate():
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def _has_current_target_area(self, parent: str, child: str) -> bool:
        text = self.body_text()
        parent_escaped = re.escape(parent)
        child_escaped = re.escape(child)
        current_area_pattern = (
            re.escape("直播分区")
            + r"[\s:：*]*"
            + parent_escaped
            + r"\s*[·・•/|｜\-]\s*"
            + child_escaped
            + r"\s*修改分区"
        )
        if re.search(current_area_pattern, text):
            return True
        separator_stripped = re.sub(r"[·・•/|｜\-\s:：*]+", "", text)
        compact_current_pattern = re.escape("直播分区" + parent + child + "修改分区")
        if re.search(compact_current_pattern, separator_stripped):
            return True
        return False

    def _collect_input_values(self) -> List[str]:
        try:
            values = self.page.evaluate(
                """
                () => Array.from(document.querySelectorAll('input, textarea'))
                  .map((el) => el.value || el.getAttribute('value') || '')
                  .filter((value) => value && value.trim().length > 0)
                """
            )
        except Exception:
            return []
        return [str(value).strip() for value in values if str(value).strip()]

    def _safe_page_excerpt(self, limit: int = 1200) -> str:
        return redact_text(self.body_text()[:limit])

    def _save_failure_diagnostics(self, reason: str) -> None:
        try:
            url = self.page.url if self.page else ""
            LOGGER.error("Browser diagnostic reason=%s url=%s body_excerpt=%s", reason, url, self._safe_page_excerpt())
            if self.settings.save_failure_screenshot and self.page:
                directory = self.settings.log_dir
                directory.mkdir(parents=True, exist_ok=True)
                path = directory / ("failure-%s-%s.png" % (reason, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")))
                self.page.screenshot(path=str(path), full_page=True)
                os.chmod(str(path), 0o600)
                LOGGER.error("Saved failure screenshot with restricted permissions: %s", path)
        except Exception as exc:
            LOGGER.warning("Failed to save browser diagnostics: %s", exc)


def _locator_text(locator: Any) -> str:
    try:
        return locator.inner_text(timeout=500)
    except Exception:
        try:
            return locator.text_content(timeout=500) or ""
        except Exception:
            return ""


def _looks_like_stream_key(value: str) -> bool:
    if not value:
        return False
    if value.startswith(("rtmp://", "rtmps://")):
        return False
    lowered = value.lower()
    if "streamname=" in lowered or "key=" in lowered:
        return True
    return value.startswith("?") and len(value) > 30
