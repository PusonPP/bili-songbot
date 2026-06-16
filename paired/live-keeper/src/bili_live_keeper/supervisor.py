"""Long-running supervisor loop and start concurrency controls."""

import fcntl
import json
import logging
import os
import signal
import time
from pathlib import Path
from typing import List, Optional

from .config import Settings
from .cookies import CookieProvider
from .starter import BiliLiveStarter, StartResult
from .status import LiveStatusChecker

LOGGER = logging.getLogger(__name__)


class StartLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._handle = None
        self.acquired = False

    def __enter__(self) -> "StartLock":
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.lock_path.open("a+")
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.acquired = True
        except BlockingIOError:
            self.acquired = False
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self._handle:
            try:
                if self.acquired:
                    fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            finally:
                self._handle.close()


class StartAttemptStore:
    def __init__(self, path: Path):
        self.path = path

    def recent_attempts(self, now: Optional[float] = None) -> List[float]:
        now = time.time() if now is None else now
        attempts = self._load()
        return [stamp for stamp in attempts if now - stamp <= 3600]

    def can_attempt(self, max_per_hour: int, now: Optional[float] = None) -> bool:
        return len(self.recent_attempts(now)) < max_per_hour

    def cooldown_remaining(self, cooldown_seconds: int, now: Optional[float] = None) -> int:
        now = time.time() if now is None else now
        attempts = self.recent_attempts(now)
        if not attempts:
            return 0
        elapsed = now - max(attempts)
        return max(0, int(cooldown_seconds - elapsed))

    def record_attempt(self, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        attempts = self.recent_attempts(now)
        attempts.append(now)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = Path(str(self.path) + ".tmp")
        tmp_path.write_text(json.dumps(attempts), encoding="utf-8")
        try:
            os.chmod(str(tmp_path), 0o640)
        except OSError:
            pass
        tmp_path.replace(self.path)
        try:
            os.chmod(str(self.path), 0o640)
        except OSError:
            pass

    def _load(self) -> List[float]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        result: List[float] = []
        for value in data:
            try:
                result.append(float(value))
            except (TypeError, ValueError):
                continue
        return result


class Supervisor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cookie_provider = CookieProvider(settings.biliup_cookie_file)
        self.checker = LiveStatusChecker(settings, self.cookie_provider)
        self.starter = BiliLiveStarter(settings, self.cookie_provider)
        self.lock_path = settings.state_dir / "start.lock"
        self.attempt_store = StartAttemptStore(settings.state_dir / "start-attempts.json")
        self.stop_requested = False
        self.stop_confirmations = 0
        self.consecutive_failures = 0

    def run_forever(self) -> None:
        self.settings.state_dir.mkdir(parents=True, exist_ok=True)
        signal.signal(signal.SIGTERM, self._request_stop)
        signal.signal(signal.SIGINT, self._request_stop)
        LOGGER.info(
            "Supervisor started interval=%ss confirm_times=%s cooldown=%ss max_attempts_per_hour=%s dry_run=%s",
            self.settings.check_interval_seconds,
            self.settings.stop_confirm_times,
            self.settings.start_cooldown_seconds,
            self.settings.max_start_attempts_per_hour,
            self.settings.dry_run,
        )
        while not self.stop_requested:
            sleep_seconds = self.settings.check_interval_seconds
            try:
                status = self.checker.check()
                self.consecutive_failures = 0
                if status.live is True:
                    self.stop_confirmations = 0
                    LOGGER.info("Heartbeat live=true source=%s reason=%s", status.source, status.reason)
                elif status.live is False:
                    self.stop_confirmations += 1
                    LOGGER.warning(
                        "Live appears stopped confirmation=%s/%s source=%s reason=%s",
                        self.stop_confirmations,
                        self.settings.stop_confirm_times,
                        status.source,
                        status.reason,
                    )
                    if self.stop_confirmations >= self.settings.stop_confirm_times:
                        result = self._attempt_start_with_guards()
                        if result and result.success:
                            self.stop_confirmations = 0
                else:
                    self.stop_confirmations = 0
                    LOGGER.warning("Live status unknown source=%s reason=%s; refusing to start", status.source, status.reason)
            except Exception as exc:
                self.consecutive_failures += 1
                LOGGER.exception("Supervisor iteration failed: %s", exc)
                if self.consecutive_failures >= 10:
                    raise
                sleep_seconds = min(300, self.settings.check_interval_seconds * (2 ** min(self.consecutive_failures, 5)))
                LOGGER.warning("Backing off for %s seconds after failure %s", sleep_seconds, self.consecutive_failures)
            self._sleep_interruptibly(sleep_seconds)
        LOGGER.info("Supervisor stopped")

    def _attempt_start_with_guards(self) -> Optional[StartResult]:
        with StartLock(self.lock_path) as lock:
            if not lock.acquired:
                LOGGER.warning("Another start operation holds the lock; skipping this cycle")
                return None
            cooldown = self.attempt_store.cooldown_remaining(self.settings.start_cooldown_seconds)
            if cooldown > 0:
                LOGGER.warning("Start cooldown active; %s seconds remaining", cooldown)
                return None
            if not self.attempt_store.can_attempt(self.settings.max_start_attempts_per_hour):
                LOGGER.error(
                    "Start attempt limit reached: max_start_attempts_per_hour=%s. Automatic start is paused until the rolling window clears.",
                    self.settings.max_start_attempts_per_hour,
                )
                return None
            result = self.starter.start_live_if_needed(dry_run=self.settings.dry_run)
            if not self.settings.dry_run and result.start_click_attempted:
                self.attempt_store.record_attempt()
            if result.success:
                LOGGER.info(
                    "Start workflow result action=%s reason=%s start_click_attempted=%s",
                    result.action,
                    result.reason,
                    result.start_click_attempted,
                )
            else:
                LOGGER.error(
                    "Start workflow failed reason=%s start_click_attempted=%s error=%s",
                    result.reason,
                    result.start_click_attempted,
                    result.error,
                )
            return result

    def _request_stop(self, signum, frame) -> None:  # type: ignore[no-untyped-def]
        LOGGER.info("Received signal %s; stopping after current iteration", signum)
        self.stop_requested = True

    def _sleep_interruptibly(self, seconds: int) -> None:
        deadline = time.time() + seconds
        while not self.stop_requested and time.time() < deadline:
            time.sleep(min(1.0, deadline - time.time()))


def run_start_once_with_lock(settings: Settings, dry_run: Optional[bool] = None) -> StartResult:
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    with StartLock(settings.state_dir / "start.lock") as lock:
        if not lock.acquired:
            return StartResult(False, "locked", "another_start_operation_in_progress", dry_run if dry_run is not None else settings.dry_run)
        return BiliLiveStarter(settings).start_live_if_needed(dry_run=dry_run)
