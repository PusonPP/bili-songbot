"""Command line interface."""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .config import ConfigError, load_settings
from .cookies import CookieProvider
from .logging_utils import setup_logging
from .pusher import KeepalivePusher
from .status import LiveStatusChecker
from .stopper import BiliLiveStopper
from .supervisor import Supervisor, run_start_once_with_lock


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bili-live-keeper")
    parser.add_argument("--env-file", type=Path, default=None, help="Path to .env file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Run one live status check and print JSON")

    start_parser = subparsers.add_parser("start-once", help="Run one guarded start-live workflow")
    start_parser.add_argument("--dry-run", action="store_true", help="Do not click the start-live button")

    subparsers.add_parser("stop-once", help="Explicitly stop live once by clicking the close-live button")

    subparsers.add_parser("daemon", help="Run the long-running supervisor")
    subparsers.add_parser("push-keepalive", help="Run FFmpeg keepalive pusher from runtime stream env")

    config_parser = subparsers.add_parser("print-config", help="Print effective configuration")
    config_parser.add_argument("--redacted", action="store_true", help="Print with sensitive values redacted")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = load_settings(args.env_file)
        file_logging = settings.log_dir if args.command == "daemon" else None
        setup_logging(settings.log_level, file_logging)

        if args.command == "print-config":
            print(settings.to_json(redacted=True))
            return 0

        if args.command == "check":
            settings.validate_for_check()
            checker = LiveStatusChecker(settings, CookieProvider(settings.biliup_cookie_file))
            print(checker.check().to_json())
            return 0

        if args.command == "start-once":
            settings.validate_for_start()
            result = run_start_once_with_lock(settings, dry_run=True if args.dry_run else None)
            print(result.to_json())
            return 0 if result.success else 1

        if args.command == "stop-once":
            settings.validate_for_start()
            result = BiliLiveStopper(settings).stop_live_if_live()
            print(result.to_json())
            return 0 if result.success else 1

        if args.command == "daemon":
            settings.validate_for_start()
            Supervisor(settings).run_forever()
            return 0

        if args.command == "push-keepalive":
            KeepalivePusher(settings).run_forever()
            return 0

        parser.error("unknown command: %s" % args.command)
        return 2
    except ConfigError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
