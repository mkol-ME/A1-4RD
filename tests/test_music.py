import io
import sys
import threading
import time
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "client"))

import music


class FakeOutput:
    def __init__(self):
        self.blocks = []
        self.started = self.closed = False

    def start(self):
        self.started = True

    def write(self, block):
        self.blocks.append(block.copy())
        time.sleep(0.001)

    def stop(self):
        pass

    def close(self):
        self.closed = True


class SlowStream(io.BytesIO):
    """PCM that is read like a network stream, recording how much was taken."""

    def read(self, size=-1):
        time.sleep(0.002)
        return super().read(size)


def pcm(seconds: float, level: int = 16000) -> bytes:
    frames = int(seconds * music.RATE)
    return np.full(frames * music.CHANNELS, level, dtype="<i2").tobytes()


def wait_for(condition, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return False


class ControlTests(unittest.TestCase):
    def test_controls(self):
        cases = {"pause": "pause", "Pause the music.": "pause", "stop": "stop", "turn it off": "stop",
                 "resume": "resume", "keep playing": "resume", "turn it up a bit": "louder",
                 "louder please": "louder", "can you turn it down": "quieter", "volume down": "quieter"}
        for prompt, action in cases.items():
            self.assertEqual(music.control(prompt), action, prompt)

    def test_requests_are_not_controls(self):
        for prompt in ("play bohemian rhapsody", "next", "whats this song", "stop being dramatic",
                       "turn off the lights"):
            self.assertIsNone(music.control(prompt), prompt)


class PlayerTests(unittest.TestCase):
    def make(self, data: bytes):
        output = FakeOutput()
        player = music.MusicPlayer(opener=lambda url: SlowStream(data), output=lambda: output)
        return player, output

    def test_plays_to_the_end_at_the_set_volume(self):
        player, output = self.make(pcm(1.0))
        player.play({"id": "abcdefghijk", "title": "t"})
        self.assertTrue(wait_for(lambda: not player.active))
        audio = np.concatenate(output.blocks)
        self.assertEqual(audio.shape, (music.RATE, 2))
        self.assertAlmostEqual(float(audio[-1, 0]), 16000 / 32768 * music.DEFAULT_VOLUME, places=4)
        self.assertTrue(output.closed)

    def test_pause_stops_reading_and_resume_continues(self):
        player, output = self.make(pcm(5.0))
        player.play({"id": "abcdefghijk"})
        self.assertTrue(wait_for(lambda: len(output.blocks) >= 3))
        player.pause()
        time.sleep(0.1)
        count = len(output.blocks)
        time.sleep(0.2)
        self.assertEqual(len(output.blocks), count)
        self.assertTrue(player.paused)
        player.resume()
        self.assertTrue(wait_for(lambda: len(output.blocks) > count))
        player.stop()
        self.assertFalse(player.active)

    def test_ducking_lowers_and_restores(self):
        player, output = self.make(pcm(5.0))
        player.play({"id": "abcdefghijk"})
        self.assertTrue(wait_for(lambda: len(output.blocks) >= 2))
        player.duck()
        self.assertTrue(wait_for(lambda: len(output.blocks) >= 6))
        ducked = float(output.blocks[-1][-1, 0])
        self.assertAlmostEqual(ducked, 16000 / 32768 * music.DEFAULT_VOLUME * music.DUCKED, places=4)
        player.unduck()
        seen = len(output.blocks)
        self.assertTrue(wait_for(lambda: len(output.blocks) >= seen + 3))
        self.assertAlmostEqual(float(output.blocks[-1][-1, 0]), 16000 / 32768 * music.DEFAULT_VOLUME, places=4)
        player.stop()

    def test_playing_something_else_replaces_it(self):
        player, output = self.make(pcm(5.0))
        player.play({"id": "abcdefghijk", "title": "first"})
        self.assertTrue(wait_for(lambda: len(output.blocks) >= 2))
        first = player._thread
        player.play({"id": "bcdefghijkl", "title": "second"})
        self.assertFalse(first.is_alive())
        self.assertEqual(player.title, "second")
        player.stop()

    def test_volume_is_bounded(self):
        player, _ = self.make(b"")
        for _ in range(20):
            player.louder()
        self.assertEqual(player.volume, 1.0)
        for _ in range(40):
            player.quieter()
        self.assertGreater(player.volume, 0)


if __name__ == "__main__":
    unittest.main()
