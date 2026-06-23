from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
import unicodedata

from PIL import Image, ImageDraw, ImageFont
import yaml

from .config import AppConfig
from .models import Song

logger = logging.getLogger(__name__)


def _font(path: Path, size: int):
    try:
        if path.exists():
            return ImageFont.truetype(str(path), size=size, index=0)
    except Exception:  # noqa: BLE001
        logger.exception("加载字体失败：%s", path)
    return ImageFont.load_default()


class UiLayerGenerator:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.output_path = cfg.abs_path(cfg.ui.output_path)
        self.font_path = cfg.abs_path(cfg.ui.font_path) if not Path(cfg.ui.font_path).is_absolute() else Path(cfg.ui.font_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.panel_text_path = self.output_path.with_suffix(".panel.txt")
        self.notice_text_path = self.output_path.with_suffix(".notice.txt")
        self._last_render_at = 0.0

    def render(self, current: Song | None, snapshot: dict[str, Any], force: bool = False) -> Path:
        now = time.time()
        if not force and self.output_path.exists() and now - self._last_render_at < self.cfg.stream.ui_refresh_min_interval:
            return self.output_path

        w, h = self.cfg.stream.output_width, self.cfg.stream.output_height
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        title_font = _font(self.font_path, 32 if h >= 720 else 24)
        item_font = _font(self.font_path, 24 if h >= 720 else 18)
        small_font = _font(self.font_path, 18 if h >= 720 else 14)
        notice_font = _font(self.font_path, 18 if h >= 720 else 14)

        # 左侧列表安全区域：尽量不覆盖右侧歌词。
        panel_x = int(w * 0.025)
        panel_y = int(h * 0.08)
        panel_w = int(w * 0.32)
        panel_h = int(h * 0.78)
        radius = 18

        draw.rounded_rectangle(
            [panel_x, panel_y, panel_x + panel_w, panel_y + panel_h],
            radius=radius,
            fill=(0, 0, 0, 118),
            outline=(255, 255, 255, 36),
            width=1,
        )

        x = panel_x + 24
        y = panel_y + 22
        draw.text((x, y), "当前播放", font=small_font, fill=(220, 220, 220, 235))
        y += 28
        current_name = current.display_name if current else "准备中"
        draw.text((x, y), _clip(current_name, 16), font=title_font, fill=(255, 255, 255, 255))
        y += 56

        draw.line([x, y, panel_x + panel_w - 24, y], fill=(255, 255, 255, 55), width=1)
        y += 18
        draw.text((x, y), "点歌队列", font=small_font, fill=(220, 220, 220, 235))
        y += 30
        draw.text((x, y), "可输入特定歌曲关键词进行点歌", font=small_font, fill=(230, 230, 230, 218))
        y += 24
        draw.text((x, y), "同一用户一分钟内只支持一次点歌", font=small_font, fill=(230, 230, 230, 218))
        y += 32

        requests = snapshot.get("request_queue", [])[: self.cfg.ui.show_request_queue]
        if requests:
            for idx, item in enumerate(requests, start=1):
                name = _clip(item.get("display_name", "未知歌曲"), 14)
                uname = _clip(item.get("uname", "匿名"), 8)
                draw.text((x, y), f"{idx}. {name}", font=item_font, fill=(255, 255, 255, 240))
                y += 28
                draw.text((x + 26, y), f"by {uname}", font=small_font, fill=(200, 200, 200, 210))
                y += 28
        else:
            draw.text((x, y), "暂无点歌，正在乱序播放", font=item_font, fill=(235, 235, 235, 225))
            y += 44

        if y < panel_y + panel_h - 130:
            draw.line([x, y, panel_x + panel_w - 24, y], fill=(255, 255, 255, 45), width=1)
            y += 18
            draw.text((x, y), "随机预告", font=small_font, fill=(220, 220, 220, 220))
            y += 30
            for idx, item in enumerate(snapshot.get("shuffle_preview", [])[: self.cfg.ui.show_random_preview], start=1):
                draw.text((x, y), f"{idx}. {_clip(item.get('display_name', ''), 14)}", font=item_font, fill=(240, 240, 240, 225))
                y += 32

        # 右上角提示。为了不压歌词，字号较小，右对齐。
        notice = self._notice_text()
        margin = int(w * 0.02)
        max_notice_w = int(w * 0.56)
        lines = _wrap_text(draw, notice, notice_font, max_notice_w)
        ny = int(h * 0.025)
        line_h = notice_font.size + 6 if hasattr(notice_font, "size") else 22
        for line in lines[:3]:
            bbox = draw.textbbox((0, 0), line, font=notice_font)
            tw = bbox[2] - bbox[0]
            tx = w - margin - tw
            # 轻微描边，保证深浅背景都可读。
            draw.text((tx + 1, ny + 1), line, font=notice_font, fill=(0, 0, 0, 185))
            draw.text((tx, ny), line, font=notice_font, fill=(255, 255, 255, 238))
            ny += line_h

        self._write_realtime_text_files(current, snapshot)

        tmp = self.output_path.with_suffix(".tmp.png")
        img.save(tmp)
        tmp.replace(self.output_path)
        self._last_render_at = now
        return self.output_path

    def _write_realtime_text_files(self, current: Song | None, snapshot: dict[str, Any]) -> None:
        """Write UTF-8 text files consumed by pusher drawtext reload=1.

        Keep each line short because FFmpeg drawtext does not wrap textfile lines.
        The left panel uses plain white text on a semi-transparent black base, so
        readability and clipping are more important than decorative styling.
        """
        current_name = current.display_name if current else "准备中"

        requests = snapshot.get("request_queue", [])[: self.cfg.ui.show_request_queue]
        if requests:
            queue_lines = []
            for idx, item in enumerate(requests[:4], start=1):
                name = _clip(item.get("display_name", "未知歌曲"), 24)
                uname = _clip(item.get("uname", "匿名"), 10)
                # Keep one compact line so it cannot overflow the panel.
                queue_lines.append(f"{idx}. {name} / {uname}")
            queue_text = "\n".join(queue_lines)
        else:
            queue_text = "暂无点歌，正在乱序播放"

        preview_items = snapshot.get("shuffle_preview", [])[: min(3, self.cfg.ui.show_random_preview)]
        preview_lines = [
            f"{idx}. {_clip(item.get('display_name', ''), 25)}"
            for idx, item in enumerate(preview_items, start=1)
        ]
        preview_text = "\n".join(preview_lines) if preview_lines else "暂无预告"

        notice = self._notice_text()
        base = self.output_path.with_suffix("")
        files = {
            "current": _clip(current_name, 24),
            "hint": "可输入歌曲关键词进行点歌\n同一用户一分钟内只支持一次",
            "queue": queue_text,
            "preview": preview_text,
            "notice": notice,
        }

        for name, text in files.items():
            path = base.with_name(base.name + f".{name}.txt")
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(str(text), encoding="utf-8")
            tmp.replace(path)

        # Backward-compatible aggregate files. They are no longer used by the new
        # pusher layout, but keeping them helps debugging and older deployments.
        aggregate_lines: list[str] = [
            "当前播放",
            _clip(current_name, 26),
            "",
            "点歌提示",
            "可输入歌曲关键词进行点歌",
            "同一用户一分钟内只支持一次",
            "",
            "点歌队列",
            queue_text,
            "",
            "随机预告",
            preview_text,
        ]
        panel_tmp = self.panel_text_path.with_suffix(".panel.tmp.txt")
        panel_tmp.write_text("\n".join(aggregate_lines), encoding="utf-8")
        panel_tmp.replace(self.panel_text_path)

        notice_tmp = self.notice_text_path.with_suffix(".notice.tmp.txt")
        notice_tmp.write_text(notice, encoding="utf-8")
        notice_tmp.replace(self.notice_text_path)

    def _notice_text(self) -> str:
        """Read the notice from app.yaml so small text updates do not require a restart."""
        try:
            raw = yaml.safe_load(self.cfg.app_config.read_text(encoding="utf-8")) or {}
            notice = (raw.get("ui") or {}).get("right_top_notice")
            if notice is not None:
                return str(notice)
        except Exception:  # noqa: BLE001
            logger.warning("读取公告配置失败，使用启动时配置：%s", self.cfg.app_config, exc_info=True)
        return str(self.cfg.ui.right_top_notice)


def _display_width(ch: str) -> int:
    # Approximate terminal/video text width. CJK full-width characters occupy
    # roughly twice the horizontal space of ASCII in the Noto CJK font.
    return 2 if unicodedata.east_asian_width(ch) in {"W", "F"} else 1


def _clip(text: str, max_chars: int) -> str:
    """Clip by approximate display width, not Python character count.

    FFmpeg drawtext does not auto-wrap textfile lines. Counting display width
    prevents mixed Chinese/English titles from crossing the left panel border.
    """
    text = str(text or "").replace("\n", " ").strip()
    if max_chars <= 1:
        return "…" if text else ""

    used = 0
    out: list[str] = []
    for ch in text:
        width = _display_width(ch)
        if used + width > max_chars:
            break
        out.append(ch)
        used += width

    if len(out) == len(text):
        return text

    # Reserve space for the ellipsis.
    while out and used + 1 > max_chars:
        used -= _display_width(out.pop())
    return "".join(out).rstrip() + "…"


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw_line in str(text or "").splitlines() or [""]:
        buf = ""
        for ch in raw_line:
            test = buf + ch
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width and buf:
                lines.append(buf)
                buf = ch
            else:
                buf = test
        if buf:
            lines.append(buf)
    return lines
