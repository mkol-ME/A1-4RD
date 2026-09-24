import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

import voice_eq  # noqa: E402

RATE = 48000


def tone(freq, seconds=0.5, level=0.3):
    t = np.arange(int(seconds * RATE)) / RATE
    return level * np.sin(2 * np.pi * freq * t)


def band_level(x, freq):
    spec = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    return spec[np.argmin(np.abs(f - freq))]


class VoiceEqTests(unittest.TestCase):
    def test_boom_down_clarity_up(self):
        mix = tone(80) + tone(3000)
        out = voice_eq.apply(mix, RATE)
        before = band_level(mix, 3000) / band_level(mix, 80)
        after = band_level(out, 3000) / band_level(out, 80)
        # 80 Hz loses about 8 dB to the high-pass and 3 kHz gains about 11.5 on the shelf.
        self.assertGreater(after / before, 8)

    def test_never_clips(self):
        loud = tone(2000, level=0.99)
        self.assertLessEqual(np.abs(voice_eq.apply(loud, RATE)).max(), voice_eq.PEAK + 1e-9)

    def test_keeps_loudness_when_there_is_room(self):
        quiet = tone(1500, level=0.05) + tone(300, level=0.05)
        out = voice_eq.apply(quiet, RATE)
        self.assertAlmostEqual(np.sqrt(np.mean(out ** 2)), np.sqrt(np.mean(quiet ** 2)), places=3)

    def test_empty_and_off(self):
        self.assertEqual(voice_eq.apply(np.zeros(0), RATE).size, 0)
        x = tone(500)
        np.testing.assert_array_equal(voice_eq.apply(x, RATE, chain=()), x)


class SettingsFileTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.folder = tempfile.mkdtemp()
        self.saved = voice_eq.SETTINGS
        voice_eq.SETTINGS = Path(self.folder) / "voice_eq.json"
        voice_eq._cache.update(mtime=None, chain=())

    def tearDown(self):
        voice_eq.SETTINGS = self.saved

    def write(self, text, bump):
        import os
        voice_eq.SETTINGS.write_text(text, encoding="utf-8")
        os.utime(voice_eq.SETTINGS, (bump, bump))          # a distinct mtime per write

    def test_no_file_means_no_eq(self):
        self.assertEqual(voice_eq.current(), ())

    def test_read_and_changed(self):
        self.write('{"chain": [["highpass", 100, 0], ["highshelf", 1000, 6]]}', 1000)
        self.assertEqual(voice_eq.current(), (("highpass", 100.0, 0.0), ("highshelf", 1000.0, 6.0)))
        self.write('{"chain": []}', 2000)
        self.assertEqual(voice_eq.current(), ())

    def test_a_broken_file_means_no_eq(self):
        for text, bump in (("not json", 1000), ('{"chain": [["lowpass", 100, 0]]}', 2000),
                           ('{"chain": [["highpass"]]}', 3000)):
            self.write(text, bump)
            self.assertEqual(voice_eq.current(), (), text)


if __name__ == "__main__":
    unittest.main()
