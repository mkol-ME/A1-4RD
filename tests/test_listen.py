"""Wake-word matching and utterance segmentation, without a microphone."""

import collections
import queue
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "client"))

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


    def test_numbers_survive(self):
        # The old pattern was [a-z']+, so every digit was deleted on the way
        # through. Whisper heard "Pokemon number 25" and he was handed
        # "pokemon number", then blamed for not knowing.
        self.assertEqual(listen.strip_wake_word("Alfred, Pokemon number 25."),
                         "pokemon number 25")
        self.assertEqual(listen.strip_wake_word("Alfred, what is 5280 feet"),
                         "what is 5280 feet")

    def test_decimals_and_model_numbers_stay_whole(self):
        self.assertEqual(
            listen.strip_wake_word("Alfred, set the nozzle to 0.4 on the Bambu P1S"),
            "set the nozzle to 0.4 on the bambu p1s")

    def test_apostrophes_and_accents_survive(self):
        self.assertEqual(listen.strip_wake_word("alfred don't bother"), "don't bother")
        self.assertEqual(listen.strip_wake_word("Alfred, Pokémon number 10."),
                         "pokémon number 10")


class Dismissal(unittest.TestCase):
    """Ending a conversation, without ending one that is still going."""

    def test_the_butler_dismissals(self):
        for line in ("that will be all", "that'll be all, Alfred",
                     "Alfred, that's all", "go to sleep", "goodnight alfred",
                     "dismissed", "ok that will be all"):
            self.assertTrue(listen.is_dismissal(line), line)

    def test_a_question_is_not_a_dismissal(self):
        # The words appear inside plenty of things that are not dismissals.
        for line in ("nevermind the brim, why is it lifting",
                     "that's all i had for lunch",
                     "should i go to sleep or finish this print",
                     "what did you say that will be all about"):
            self.assertFalse(listen.is_dismissal(line), line)


class Segmentation(unittest.TestCase):
    """Drive Microphone.next_utterance from a queue instead of a sound card."""

    def build(self, floor=0.01):
        microphone = listen.Microphone.__new__(listen.Microphone)
        microphone.blocks = queue.Queue()
        microphone.preroll = collections.deque(
            maxlen=max(1, int(listen.PREROLL_SECONDS * listen.RATE / listen.FRAME)))
        microphone.deaf = False
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

    def test_the_word_that_started_it_is_kept(self):
        # Speech crosses the threshold a syllable in. Without the pre-roll the
        # attack is thrown away, which is how "co-main event" became "Comade".
        microphone = self.build()
        self.feed(microphone, 0.25, 0.0)                      # quiet, but recent
        self.feed(microphone, 1.0, 0.2)
        self.feed(microphone, listen.SILENCE_HANGOVER + 0.2, 0.0)
        audio = microphone.next_utterance(timeout=0.2)
        self.assertGreater(len(audio) / listen.RATE, 1.2)

    def test_he_does_not_hear_himself(self):
        # His own voice reaches this microphone like anyone else's, and was
        # being transcribed and answered.
        microphone = self.build()
        microphone.deaf = True
        listen.Microphone._on_audio(
            microphone, np.full((listen.FRAME, 1), 0.2, dtype=np.float32), 0, None, None)
        self.assertTrue(microphone.blocks.empty())
        microphone.deaf = False
        listen.Microphone._on_audio(
            microphone, np.full((listen.FRAME, 1), 0.2, dtype=np.float32), 0, None, None)
        self.assertFalse(microphone.blocks.empty())

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
        self.assertFalse(microphone.ended_by_silence)


class UnfinishedSentences(unittest.TestCase):
    """A pause that stops mid-sentence is waited through; a finished one is not."""

    build, feed = Segmentation.build, Segmentation.feed

    def test_what_the_first_session_cut_in_two(self):
        for heard in ("Alfred, what should I have?", "What's the temp in-", "What's the gravitational?",
                      "Remind me to order some", "Set the nozzle temperature to", "Is it better than",
                      "I was thinking that, um", "what about the"):
            self.assertTrue(listen.sounds_unfinished(heard), heard)

    def test_finished_sentences_are_left_alone(self):
        for heard in ("What's the temp in Springfield?", "What time is it, Alfred?", "Thank you.",
                      "That'll be all.", "It's 92 degrees outside, Alfred.", "What should I do?",
                      "Alfred, good morning.", "Why do my prints keep warping?", "", None,
                      "What's the gravitational constant?", "Is it a good idea?"):
            self.assertFalse(listen.sounds_unfinished(heard), heard)

    def test_an_unfinished_pause_is_bridged(self):
        microphone, asked = self.build(), []
        self.feed(microphone, 0.8, 0.2)
        self.feed(microphone, 0.60, 0.0)       # past the hangover, inside the longer allowance
        self.feed(microphone, 0.8, 0.2)
        self.feed(microphone, listen.UNFINISHED_HANGOVER + 0.2, 0.0)
        answers = iter([True, False])
        audio = microphone.next_utterance(timeout=0.2, unfinished=lambda: asked.append(1) or next(answers))
        self.assertGreater(len(audio) / listen.RATE, 2.0)       # both halves, one utterance
        self.assertEqual(microphone.bridged, 1)
        self.assertEqual(len(asked), 2)                          # once per pause
        self.assertTrue(microphone.ended_by_silence)

    def test_a_finished_pause_ends_on_time(self):
        microphone = self.build()
        self.feed(microphone, 0.8, 0.2)
        self.feed(microphone, 0.60, 0.0)
        self.feed(microphone, 0.8, 0.2)
        self.feed(microphone, listen.UNFINISHED_HANGOVER + 0.2, 0.0)
        audio = microphone.next_utterance(timeout=0.2, unfinished=lambda: False)
        self.assertAlmostEqual(len(audio) / listen.RATE, 0.8 + listen.SILENCE_HANGOVER, delta=0.05)
        self.assertEqual(microphone.bridged, 0)

    def test_the_longer_allowance_still_runs_out(self):
        microphone = self.build()
        self.feed(microphone, 0.8, 0.2)
        self.feed(microphone, listen.UNFINISHED_HANGOVER + 0.5, 0.0)
        audio = microphone.next_utterance(timeout=0.2, unfinished=lambda: True)
        self.assertAlmostEqual(len(audio) / listen.RATE, 0.8 + listen.UNFINISHED_HANGOVER, delta=0.05)
        self.assertEqual(microphone.bridged, 0)


class EarlyTranscription(unittest.TestCase):
    """Transcription starts at the first sign of a pause, and is only kept if the pause was the end."""

    build, feed = Segmentation.build, Segmentation.feed

    def test_the_final_pause_starts_transcription_once(self):
        microphone, paused = self.build(), []
        self.feed(microphone, 1.0, 0.2)
        self.feed(microphone, listen.SILENCE_HANGOVER + 0.2, 0.0)
        audio = microphone.next_utterance(timeout=0.2, on_pause=paused.append)
        self.assertEqual(len(paused), 1)
        self.assertTrue(microphone.ended_by_silence)
        # Everything he said is in the early audio; only trailing silence is missing.
        self.assertLess(len(paused[0]), len(audio))
        self.assertAlmostEqual(len(paused[0]) / listen.RATE,
                               1.0 + listen.EARLY_TRANSCRIBE_SILENCE, delta=0.05)

    def test_drawing_breath_starts_another_and_the_last_one_counts(self):
        microphone, paused = self.build(), []
        self.feed(microphone, 0.6, 0.2)
        self.feed(microphone, 0.27, 0.0)       # past the early mark, short of the hangover
        self.feed(microphone, 0.6, 0.2)
        self.feed(microphone, listen.SILENCE_HANGOVER + 0.2, 0.0)
        audio = microphone.next_utterance(timeout=0.2, on_pause=paused.append)
        self.assertEqual(len(paused), 2)
        self.assertGreater(len(paused[1]), len(paused[0]) + 0.5 * listen.RATE)
        self.assertGreater(len(audio) / listen.RATE, 1.4)       # not cut at the breath
        self.assertAlmostEqual(microphone.longest_pause, 0.27, delta=0.04)

    def test_a_cough_never_starts_transcription(self):
        microphone, paused = self.build(), []
        self.feed(microphone, 0.1, 0.2)
        self.feed(microphone, listen.SILENCE_HANGOVER + 0.2, 0.0)
        self.feed(microphone, 1.0, 0.2)
        self.feed(microphone, listen.SILENCE_HANGOVER + 0.2, 0.0)
        microphone.next_utterance(timeout=0.2, on_pause=paused.append)
        self.assertEqual(len(paused), 1)

    def test_the_early_result_is_used_when_the_pause_was_the_end(self):
        calls = []
        early = listen.EarlyTranscript(lambda samples: calls.append(len(samples)) or ("early", 0.3))
        early.start(np.zeros(100, dtype=np.float32))
        self.assertEqual(early.take(np.zeros(200, dtype=np.float32), ended_by_silence=True), ("early", 0.3))
        self.assertEqual(calls, [100])

    def test_a_ceiling_cut_is_transcribed_whole(self):
        calls = []
        early = listen.EarlyTranscript(lambda samples: calls.append(len(samples)) or ("text", 0.3))
        early.start(np.zeros(100, dtype=np.float32))
        early.take(np.zeros(200, dtype=np.float32), ended_by_silence=False)
        self.assertEqual(calls[-1], 200)

    def test_a_failed_early_request_is_asked_again(self):
        attempts = []
        def flaky(samples):
            attempts.append(len(samples))
            if len(attempts) == 1:
                raise OSError("tunnel hiccup")
            return ("second try", 0.3)
        early = listen.EarlyTranscript(flaky)
        early.start(np.zeros(100, dtype=np.float32))
        self.assertEqual(early.take(np.zeros(200, dtype=np.float32), True), ("second try", 0.3))


if __name__ == "__main__":
    unittest.main(verbosity=2)
