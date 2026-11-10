import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.audit_lyric_audio import flac_streaminfo, inspect_audio
from scripts import build_lyric_media


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg unavailable")
class AudioIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "audio.flac"
        subprocess.run([
            "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=1:sample_rate=44100",
            "-ac", "2", "-c:a", "flac", "-sample_fmt", "s16", "-threads", "1", str(self.path),
        ], capture_output=True, check=True)

    def test_complete_pcm_matches_streaminfo(self):
        result = inspect_audio(self.path)
        self.assertTrue(result["integrity_passed"])
        self.assertEqual(result["decoded_samples"], 44100)
        self.assertEqual(result["pcm_md5"], result["header"]["md5"])
        self.assertEqual(result["listening_review"], "not_performed")

    def test_incorrect_sample_count_is_not_repaired_by_guessing_duration(self):
        data = bytearray(self.path.read_bytes())
        value = int.from_bytes(data[18:26], "big")
        data[18:26] = ((value & ~((1 << 36) - 1)) | 88200).to_bytes(8, "big")
        self.path.write_bytes(data)
        result = inspect_audio(self.path)
        self.assertIn("flac_sample_count_mismatch", result["failures"])
        self.assertFalse(result["integrity_passed"])

    def test_corrupt_md5_fails_even_when_ffmpeg_succeeds(self):
        data = bytearray(self.path.read_bytes())
        data[26] ^= 1
        self.path.write_bytes(data)
        result = inspect_audio(self.path)
        self.assertEqual(result["decoder_exit"], 0)
        self.assertIn("flac_pcm_md5_mismatch", result["failures"])
        self.assertFalse(result["integrity_passed"])

    def test_truncated_frame_never_passes(self):
        self.path.write_bytes(self.path.read_bytes()[:-200])
        self.assertFalse(inspect_audio(self.path)["integrity_passed"])

    def test_invalid_header_rejected(self):
        self.path.write_bytes(b"fLaC\x00\x00\x00\x22short")
        with self.assertRaises(ValueError):
            flac_streaminfo(self.path)

    def test_master_builder_rejects_corrupt_source_before_encoding(self):
        data = bytearray(self.path.read_bytes())
        data[26] ^= 1
        self.path.write_bytes(data)
        root = self.path.parent
        folder = root / "song_001"
        folder.mkdir()
        shutil.copy2(self.path, folder / "audio.flac")
        (folder / "cover.png").touch()
        (root / "manifest.json").write_text(json.dumps([{
            "song_id": "song_001", "status": "structural_validation_passed",
            "audio_duration": 1,
        }]))
        with patch("sys.argv", ["build_lyric_media", str(root)]):
            with self.assertRaisesRegex(ValueError, "Source audio failed integrity"):
                build_lyric_media.main()
        self.assertFalse((folder / "clean.mp4").exists())
        self.assertFalse((folder / "clean.partial.mp4").exists())


if __name__ == "__main__":
    unittest.main()
