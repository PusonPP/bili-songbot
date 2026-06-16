from __future__ import annotations

import asyncio
import logging
import sys

from .config import load_config
from .controller import SongbotApp
from .logging_setup import setup_logging


async def async_main() -> int:
    cfg = load_config()
    setup_logging(cfg.abs_path(cfg.log_dir))
    logger = logging.getLogger(__name__)
    logger.info("bili-songbot root=%s", cfg.root_dir)
    app = SongbotApp(cfg)
    try:
        await app.start()
    finally:
        await app.stop()
    return 0


def main() -> None:
    try:
        raise SystemExit(asyncio.run(async_main()))
    except KeyboardInterrupt:
        raise SystemExit(0)
    except Exception as e:  # noqa: BLE001
        logging.exception("服务启动失败：%s", e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
