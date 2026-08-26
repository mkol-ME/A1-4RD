"""Wake-word matching and utterance segmentation, without a microphone."""

import queue
import unittest

import numpy as np

import listen


class WakeWord(unittest.TestCase):
    def test_addressed_plainly(self):
        self.assertEqual(listen.strip_wake_word("Alfred, why is my first layer lifting?"),
                         "why is my first layer lifting")

    def test_name_alone_is_a_summons(self):
        self.assertEqual(listen.strip_wake_word("Alfred."), "")

    def test_name_a_little_way_in(self):
        self.assertEqual(listen.strip_wake_word("Hey Alfred, what temperature for PETG?"),
                         "what temperature for petg")

    def test_mishearings_still_wake_him(self):
        for heard in ("Alfie, are you there?", "Alford, what about the bed?",
                      "Al Fred, is it done?", "Alfredo, check the print."):
            self.assertIsNotNone(listen.strip_wake_word(heard), heard)

    def test_not_addressed(self):
        self.assertIsNone(listen.strip_wake_word("what temperature should i run petg at"))

    def test_name_buried_late_is_not_a_summons(self):
        # Talking about him is not talking to him.
        self.assertIsNone(listen.strip_wake_word(
            "i was telling Sam the other day that Alfred is quite rude"))

    def test_silence_transcribes_to_nothing(self):
        self.assertIsNone(listen.strip_wake_word(""))
        self.assertIsNone(listen.strip_wake_word("..."))


class Segmentation(unittest.TestCase):
    """Drive Microphone.next_utterance from a queue instead of a sound card."""

    def build(self, floor=0.01):
        microphone = listen.Microphone.__new__(listen.Microphone)
        microphone.blocks = queue.Queue()
        microphone.floor = floor
        return microphone

    def feed(self, microphone, seconds, level):
        for _ in range(int(seconds * listen.RATE / listen.FRAME)):
            microphone.blocks.put(np.full(listen.FRAME, level, dtype=np.float32))

    def test_speech_then_pause_ends_the_utterance(self):
        microphone = self.build()
        self.feed(microphone, 0.0, 0.0)
        self.feed(microphone, 1.0, 0.2)                       # a second of speech
        self.feed(microphone, listen.SILENCE_HANGOVER + 0.2, 0.0)
        audio = microphone.next_utterance(timeout=0.2)
        self.assertGreater(len(audio) / listen.RATE, 1.0)

    def test_a_cough_is_ignored(self):
        microphone = self.build()
        self.feed(microphone, 0.1, 0.2)                       # too short to be speech
        self.feed(microphone, listen.SILENCE_HANGOVER + 0.2, 0.0)
        self.feed(microphone, 1.0, 0.2)                       # then something real
        self.feed(microphone, listen.SILENCE_HANGOVER + 0.2, 0.0)
        audio = microphone.next_utterance(timeout=0.2)
        self.assertGreater(len(audio) / listen.RATE, 1.0)

    def test_room_noise_alone_never_triggers(self):
        microphone = self.build()
        self.feed(microphone, 3.0, 0.02)                      # above floor, below margin
        microphone.blocks.put(np.full(listen.FRAME, 0.2, dtype=np.float32))
        self.feed(microphone, listen.SILENCE_HANGOVER + 0.5, 0.0)
        # It waits through all the noise, starts on the loud block, then finds
        # that one block too short to be speech and goes back to waiting.
        self.assertIsNone(microphone.next_utterance(timeout=0.2))

    def test_a_long_ramble_is_cut_at_the_ceiling(self):
        microphone = self.build()
        self.feed(microphone, listen.MAX_UTTERANCE + 2.0, 0.2)
        audio = microphone.next_utterance(timeout=0.2)
        self.assertLessEqual(len(audio) / listen.RATE, listen.MAX_UTTERANCE + 0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
