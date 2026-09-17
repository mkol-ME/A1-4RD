"""Keeping every utterance: what lands on disk, what the index says, and what the cap drops."""

import io
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

import audio_archive


def clip(seconds: float = 1.0) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * int(16000 * seconds))
    return buffer.getvalue()


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.archive = audio_archive.Archive(Path(self.tempdir.name) / "audio", cap_bytes=10 ** 9)

    def tearDown(self):
        self.archive.close()
        self.tempdir.cleanup()

    def test_a_clip_lands_on_disk_with_its_transcript(self):
        path = self.archive.keep(clip(1.5), "what time is it", language="en")
        self.assertTrue(path.exists())
        self.assertEqual(path.suffix, ".wav")
        row = self.archive.db.execute("SELECT seconds, language, source, text FROM clips").fetchone()
        self.assertEqual(row[1:], ("en", "voice", "what time is it"))
        self.assertAlmostEqual(row[0], 1.5, places=2)

    def test_clips_in_the_same_second_do_not_overwrite_each_other(self):
        first = self.archive.keep(clip(0.2), "one")
        second = self.archive.keep(clip(0.2), "two")
        self.assertNotEqual(first, second)
        self.assertEqual(self.archive.stats()["clips"], 2)

    def test_the_cap_drops_the_oldest_first(self):
        self.archive.cap_bytes = len(clip(1.0)) * 2 + 100
        for text in ("oldest", "middle", "newest"):
            self.archive.keep(clip(1.0), text)
        kept = [row[0] for row in self.archive.db.execute("SELECT text FROM clips ORDER BY id")]
        self.assertEqual(kept, ["middle", "newest"])
        self.assertLessEqual(self.archive.total_bytes(), self.archive.cap_bytes)
        on_disk = list((Path(self.tempdir.name) / "audio").rglob("*.wav"))
        self.assertEqual(len(on_disk), 2)

    def test_without_the_array_it_does_nothing_and_says_so(self):
        missing = audio_archive.Archive(Path(self.tempdir.name) / "no" / "such" / "place")
        self.assertFalse(missing.enabled)
        self.assertIsNone(missing.keep(clip(), "ignored"))
        self.assertEqual(missing.stats(), {"enabled": False})


if __name__ == "__main__":
    unittest.main()
