from __future__ import annotations

import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

import pysubs2
import yaml
from PIL import Image

from bili_songbot.config import AppConfig
from bili_songbot.controller import SongbotApp
from bili_songbot.lyrics import LyricCue, bilingual_ass, read_bilingual_lrc, validate_cues
from bili_songbot.models import RuntimeStatus, Song
from bili_songbot.renderer import FFmpegRenderer
from scripts.import_lyrics import apply_reference_timing, correct_text
from scripts import import_lyrics

FONT = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")


class LrcTests(unittest.TestCase):
    def test_blank_cue_clears_before_instrumental(self):
        cues = read_bilingual_lrc("[00:01.00]one\n[00:02.00]\n[00:15.00]two", "first\nsecond", 20)
        self.assertEqual((cues[0].end_ms, cues[0].end_basis), (2000, "explicit_clear"))

    def test_short_lines_do_not_overlap(self):
        cues = read_bilingual_lrc("[00:01.00]one\n[00:01.35]two\n[00:01.70]", "first\nsecond", 5)
        self.assertEqual([(c.start_ms, c.end_ms) for c in cues], [(1000, 1350), (1350, 1700)])

    def test_duplicate_text_keeps_occurrence_translation(self):
        cues = read_bilingual_lrc("[00:01.00]same\n[00:02.00]same", "first\nsecond", 8)
        self.assertEqual([c.translation for c in cues], ["first", "second"])

    def test_multiple_timestamps_share_one_translation(self):
        cues = read_bilingual_lrc("[00:03.00][00:01.00]same", "first", 8)
        self.assertEqual([c.start_ms for c in cues], [1000, 3000])
        self.assertEqual([c.translation for c in cues], ["first", "first"])

    def test_precision_and_offset(self):
        cues = read_bilingual_lrc("[offset:+250]\n[00:01.005]one\n[00:02.5]", "first", 5)
        self.assertEqual((cues[0].start_ms, cues[0].end_ms), (1255, 2750))

    def test_bom_and_metadata(self):
        cues = read_bilingual_lrc("\ufeff[ar:artist]\n[ti:title]\n[00:01.00]one", "first", 5)
        self.assertEqual(cues[0].original, "one")

    def test_missing_or_extra_translation_fails(self):
        for zh in ["", "first\nsecond"]:
            with self.subTest(zh=zh), self.assertRaises(ValueError):
                read_bilingual_lrc("[00:01.00]one", zh, 10)

    def test_bad_times_fail(self):
        for lrc in ["[00:60.00]one", "[00:01.00]one\n[00:01.00]", "[00:11.00]one", "[offset:-2000]\n[00:01.00]one", "[broken]one", "[offset:invalid]\n[00:01.00]one"]:
            with self.subTest(lrc=lrc), self.assertRaises(ValueError):
                read_bilingual_lrc(lrc, "first", 10)

    def test_last_line_end_is_honestly_flagged_and_clamped(self):
        cue = read_bilingual_lrc("[00:08.00]one", "first", 10)[0]
        self.assertEqual((cue.end_ms, cue.end_basis), (10000, "unverified_last_line_hold"))

    def test_invalid_duration(self):
        for duration in [0, -1, float("inf"), float("nan")]:
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                read_bilingual_lrc("[00:01.00]one", "first", duration)

    def test_validation_rejects_overlap_and_subcentisecond(self):
        a = LyricCue(1000, 2000, "one", "first", 1)
        for cues in [[a, replace(a, start_ms=1500)], [replace(a, end_ms=1001)]]:
            with self.assertRaises(ValueError):
                validate_cues(cues, 5)

    def test_patch_fails_if_original_changes(self):
        with self.assertRaises(ValueError):
            correct_text("[00:01.00]one", "first", True, [{"line": 1, "before": "wrong", "translation": "new"}])

    def test_patch_preserves_blank_cues(self):
        raw, zh = correct_text("[00:01.00]one\n[00:02.00]", "first", True,
                               [{"line": 1, "before": "one", "original": "ONE", "translation": "new"}])
        self.assertIn("[00:02.00]", raw)
        self.assertEqual(read_bilingual_lrc(raw, zh, 5)[0].translation, "new")

    def test_reference_groups_preserve_all_text_without_interpolation(self):
        ref = {"groups": [{"provided_lines": [1, 2], "start_ms": 1000},
                          {"provided_lines": [3], "start_ms": 4500}], "clear_ms": [3000]}
        lrc, zh = apply_reference_timing("a\nb\nc", "A\nB\nC", ref)
        cues = read_bilingual_lrc(lrc, zh, 9)
        self.assertEqual([c.original for c in cues], ["a / b", "c"])
        self.assertEqual([c.translation for c in cues], ["A / B", "C"])
        self.assertEqual(cues[0].end_ms, 3000)

    def test_reference_rejects_missing_repeated_or_reordered_lines(self):
        for groups in [[1], [1, 1], [2, 1], [1, 3]]:
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                apply_reference_timing("a\nb", "A\nB", {"groups": [{"provided_lines": groups, "start_ms": 1000}]})

    @unittest.skipUnless(FONT.is_file(), "CJK font unavailable")
    def test_ass_carry_escape_layout_and_roundtrip(self):
        cue = LyricCue(59999, 62000, r"literal {\pos(0,0)} " + "界" * 100, "文" * 100, 1)
        subs = bilingual_ass([cue], "title", 65, FONT)
        text = subs.to_string("ass")
        parsed = pysubs2.SSAFile.from_string(text, format_="ass")
        self.assertEqual(parsed.events[-1].start, 59990)
        self.assertNotIn(":60.", text)
        self.assertNotIn(r"{\pos(0,0)}", text)
        self.assertIn(r"\pos(850,365)", text)


class BlockedReferenceTests(unittest.TestCase):
    def test_blocked_candidate_cannot_create_deployable_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "raw.txt").write_text("one\ntwo\n")
            (root / "zh.txt").write_text("first\nsecond\n")
            (root / "config/songs.yaml").write_text(yaml.safe_dump({
                "songs": [{"song_id": "song_003", "display_name": "test"}]}))
            (root / "config/lyric_corrections.yaml").write_text("corrections: {}\n")
            (root / "manifest.json").write_text(json.dumps([{
                "song_id": "song_003", "raw": "raw.txt", "translation": "zh.txt",
                "format": ".txt", "audio_duration": 10,
            }]))
            (root / "reference.json").write_text(json.dumps({"song_003": {
                "source_sha256": hashlib.sha256((root / "raw.txt").read_bytes()).hexdigest(),
                "audio_duration": 10, "blocked_reason": "needs_listening",
                "groups": [{"provided_lines": [1, 2], "start_ms": 1000}],
            }}))
            output = root / "release"
            with patch.object(import_lyrics, "ROOT", root), patch("sys.argv", [
                "import_lyrics", "--manifest", str(root / "manifest.json"),
                "--output", str(output), "--reference-index", str(root / "reference.json"),
            ]):
                import_lyrics.main()
            result = json.loads((output / "manifest.json").read_text())[0]
            self.assertEqual(result["status"], "blocked_reference")
            self.assertEqual(result["block_reason"], "needs_listening")
            self.assertFalse((output / "song_003/lyrics.ass").exists())
            self.assertFalse((output / "song_003/cues.json").exists())

    def test_all_pending_reference_candidates_remain_blocked(self):
        path = Path(__file__).resolve().parents[1] / "config/lyric_review_candidates.json"
        candidates = json.loads(path.read_text())
        self.assertEqual(set(candidates), {"song_003", "song_004", "song_016", "song_023"})
        for reference in candidates.values():
            self.assertTrue(reference["blocked_reason"])
            self.assertEqual(reference["listening_review"], "not_performed")
            self.assertIsInstance(reference["reference_song_id"], int)


class PlaybackTests(unittest.IsolatedAsyncioTestCase):
    def test_renderer_resolves_updated_subtitle_link_on_next_chunk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, new, link = root / "old.ass", root / "new.ass", root / "live.ass"
            old.touch()
            new.touch()
            link.symlink_to(old)
            cfg = AppConfig(root, root / "songs", root / "app", root / "env")
            renderer = FFmpegRenderer(cfg, Mock())
            song = Song("one", "one", "one.mp4", [], lyrics_file_path="live.ass")
            self.assertIn(f"ass=filename='{old}'", renderer._song_video_filter(song, 0))
            temporary = root / "next.ass"
            temporary.symlink_to(new)
            temporary.replace(link)
            self.assertIn(f"ass=filename='{new}'", renderer._song_video_filter(song, 20))

    async def test_controller_plays_full_tail_and_next_intro(self):
        app = SongbotApp.__new__(SongbotApp)
        app.cfg = AppConfig(Path("."), Path("songs"), Path("app"), Path("env"))
        app.status = RuntimeStatus()
        app.storage = Mock()
        app.queue = Mock(mark_played=AsyncMock(), snapshot=AsyncMock(return_value={}), get_next_song=AsyncMock())
        song = Song("one", "one", "one.mp4", [], duration=21.23)
        following = Song("two", "two", "two.mp4", [], duration=25)
        app.queue.get_next_song.return_value = following
        app.ui = Mock()
        app.renderer = Mock(render_song_chunk=AsyncMock(), render_transition=AsyncMock(), last_transition_next_visible=0)
        await app._play_one_song_then_transition(song, 0)
        chunks = app.renderer.render_song_chunk.call_args_list
        self.assertAlmostEqual(sum(c.args[2] for c in chunks), song.duration)
        self.assertEqual(app._next_start_offset_after_transition, 0)

    async def test_transition_holds_frame_and_consumes_no_intro(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "transition.mov").touch()
            cfg = AppConfig(root, root / "songs", root / "app", root / "env")
            renderer = FFmpegRenderer(cfg, Mock())
            renderer._probe_duration = Mock(return_value=2.15)
            renderer._run_and_push = AsyncMock()
            a, b = Song("a", "a", "a.mp4", [], duration=20), Song("b", "b", "b.mp4", [], duration=20)
            a.transition_policy.transition_asset = "transition.mov"
            await renderer.render_transition(a, b, root / "unused.png")
            self.assertEqual(renderer.last_transition_next_visible, 0)
            command = renderer._run_and_push.call_args.args[0]
            filters = command[command.index("-filter_complex") + 1]
            self.assertIn("trim=end_frame=1", filters)
            self.assertIn("anullsrc", filters)


@unittest.skipUnless(shutil.which("ffmpeg") and FONT.is_file(), "FFmpeg/font unavailable")
class FFmpegTimingTests(unittest.TestCase):
    def test_seek_uses_absolute_lyrics_at_chunk_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = AppConfig(root, root / "songs", root / "app", root / "env")
            cues = [LyricCue(19500, 20500, "BOUNDARY", "BOUNDARY", 1)]
            bilingual_ass(cues, "TITLE", 22, FONT).save(str(root / "test.ass"))
            renderer = FFmpegRenderer(cfg, Mock())
            song = Song("test", "test", "unused", [], lyrics_file_path="test.ass")
            counts = []
            for start in [19.0, 20.0, 21.0]:
                target = root / f"{int(start)}.png"
                subprocess.run([
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-filter_complex_threads", "1",
                    "-f", "lavfi", "-i", "color=black:s=1280x720:r=30:d=1",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                    "-filter_complex", renderer._song_video_filter(song, start).replace("[0:a]", "[1:a]"),
                    "-map", "[v]", "-frames:v", "1", "-threads", "1", str(target),
                ], check=True, capture_output=True, timeout=30)
                with Image.open(target) as frame:
                    pixels = frame.convert("L").crop((470, 260, 1230, 470))
                    counts.append(sum(value > 100 for value in pixels.getdata()))
            self.assertEqual(counts[0], 0)
            self.assertGreater(counts[1], 500)
            self.assertEqual(counts[2], 0)


if __name__ == "__main__":
    unittest.main()
