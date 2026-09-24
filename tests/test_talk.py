import io
import queue
import sys
import unittest
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "client"))

import listen  # noqa: E402
import talk    # noqa: E402


def clip(seconds: float = 0.5) -> bytes:
    """A WAV of a tone at the player's rate."""
    t = np.arange(int(seconds * talk.SAMPLE_RATE)) / talk.SAMPLE_RATE
    pcm = (np.sin(2 * np.pi * 220 * t) * 12000).astype("<i2")
    out = io.BytesIO()
    with wave.open(out, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(talk.SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())
    return out.getvalue()


class FakeStream:
    latency = 0.0

    def __init__(self, on_write=None):
        self.writes = 0
        self.on_write = on_write

    def write(self, block):
        self.writes += 1
        if self.on_write:
            self.on_write()
        return False


def player(stream):
    made = talk.Player.__new__(talk.Player)     # no audio device, no thread
    made.generation, made.deadline, made.dropouts, made.pause_scale = 0, 0.0, 0, 1.0
    made.stream = stream
    made.queue = queue.Queue()
    return made


class InterruptTests(unittest.TestCase):
    def setUp(self):
        self.saved, talk.audio_log = talk.audio_log, lambda *args, **kwargs: None

    def tearDown(self):
        talk.audio_log = self.saved

    def test_a_whole_sentence_plays_when_left_alone(self):
        stream = FakeStream()
        player(stream)._play(0, clip(), "Hello.")
        self.assertGreater(stream.writes, 10)

    def test_interrupt_stops_mid_sentence(self):
        made = None
        stream = FakeStream(on_write=lambda: made.interrupt())
        made = player(stream)
        made._play(0, clip(), "A long sentence.")
        self.assertEqual(stream.writes, 1)

    def test_sentences_queued_before_an_interrupt_are_dropped(self):
        stream = FakeStream()
        made = player(stream)
        made.submit(clip(), "Queued.")
        made.interrupt()
        made._play(*made.queue.get())
        self.assertEqual(stream.writes, 0)


class ListenStopTests(unittest.TestCase):
    def test_a_quiet_room_returns_once_told_to_stop(self):
        mic = listen.Microphone.__new__(listen.Microphone)
        mic.blocks = queue.Queue()
        mic.preroll = listen.collections.deque(maxlen=4)
        mic.floor = 0.01
        for _ in range(50):
            mic.blocks.put(np.zeros(listen.FRAME, dtype=np.float32))
        asked = []
        got = mic.next_utterance(timeout=0.1, stop=lambda: asked.append(1) or len(asked) > 3)
        self.assertIsNone(got)
        self.assertEqual(len(asked), 4)

    def test_stop_words_end_the_turn(self):
        self.assertIn("stop", listen.STOP_WORDS)
        self.assertEqual(listen.strip_wake_word("Alfred, next."), "next")
        self.assertEqual(listen.strip_wake_word("Alfred."), "")
        self.assertIsNone(listen.strip_wake_word("Rosas Junior over Barcelos, sixty five percent."))


if __name__ == "__main__":
    unittest.main()
