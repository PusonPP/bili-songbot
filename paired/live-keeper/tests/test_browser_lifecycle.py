"""Startup failures must not poison the next supervisor iteration."""

import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from bili_live_keeper.browser import BiliLiveBrowser


class BrowserLifecycleTests(unittest.TestCase):
    def test_failed_launch_releases_real_playwright_loop_and_allows_retry(self):
        settings = SimpleNamespace(
            chromium_executable=Path('/nonexistent-songbot-test-browser'),
            headless=True,
        )
        provider = Mock()
        for _ in range(2):
            browser = BiliLiveBrowser(settings, provider)
            try:
                with self.assertRaisesRegex(Exception, "(?i)executable doesn't exist"):
                    with browser:
                        self.fail('Invalid executable unexpectedly launched')
                with self.assertRaises(RuntimeError):
                    asyncio.get_running_loop()
                self.assertIsNone(browser._playwright)
                self.assertIsNone(browser.browser)
                provider.load.assert_not_called()
            finally:
                browser.close()

    def test_partial_context_is_closed_even_when_one_cleanup_fails(self):
        browser = BiliLiveBrowser(SimpleNamespace(), Mock())
        context, process, playwright = Mock(), Mock(), Mock()
        context.close.side_effect = RuntimeError('Context already disconnected')
        original_error = OSError('Startup interrupted')

        def fail_after_context_creation():
            browser.context = context
            browser.browser = process
            browser._playwright = playwright
            raise original_error

        browser.start = fail_after_context_creation
        with self.assertRaises(OSError) as raised:
            with browser:
                self.fail('Startup unexpectedly succeeded')
        self.assertIs(raised.exception, original_error)
        context.close.assert_called_once()
        process.close.assert_called_once()
        playwright.stop.assert_called_once()
        self.assertIsNone(browser.context)
        self.assertIsNone(browser.browser)
        self.assertIsNone(browser._playwright)


if __name__ == '__main__':
    unittest.main()
