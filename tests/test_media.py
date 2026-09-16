import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

import media


class MediaParseTests(unittest.TestCase):
    def test_play_requests(self):
        cases = {
            "play bohemian rhapsody": "bohemian rhapsody",
            "can you play bohemian rhapsody by queen": "bohemian rhapsody by queen",
            "put on some lofi hip hop": "lofi hip hop",
            "play mr brightside on youtube": "mr brightside",
            "Hey, could you play Clair de Lune please?": "clair de lune",
            "throw on the new kendrick album": "the new kendrick album",
        }
        for prompt, query in cases.items():
            self.assertEqual(media.parse(prompt), ("play", query), prompt)

    def test_search_requests(self):
        cases = {
            "find videos of cats falling off tables": "cats falling off tables",
            "search youtube for bambu p1s calibration": "bambu p1s calibration",
            "show me some videos about the james webb telescope": "the james webb telescope",
            "look up benchy speed runs on youtube": "benchy speed runs",
            "find me a video on how to change a nozzle": "how to change a nozzle",
        }
        for prompt, query in cases.items():
            self.assertEqual(media.parse(prompt), ("search", query), prompt)

    def test_picking_needs_results(self):
        self.assertEqual(media.parse("play the second one", have_results=True), ("pick", 2))
        self.assertEqual(media.parse("the first one", have_results=True), ("pick", 1))
        self.assertEqual(media.parse("number 3", have_results=True), ("pick", 3))
        self.assertEqual(media.parse("next", have_results=True), ("next", None))
        self.assertEqual(media.parse("skip this song", have_results=True), ("next", None))
        self.assertIsNone(media.parse("the first one"))

    def test_not_media(self):
        for prompt in ("what should i play tonight", "whats the weather like", "play it again",
                       "i want to play a game", "who plays in the super bowl",
                       "find out what time the cubs play tonight", "tell me a joke"):
            self.assertIsNone(media.parse(prompt), prompt)

    def test_spoken_title(self):
        self.assertEqual(media.spoken_title({"title": "Queen – Bohemian Rhapsody (Official Video Remastered)"}),
                         "Queen, Bohemian Rhapsody")
        self.assertEqual(media.spoken_title({"title": "Mr. Brightside [HD] | The Killers"}), "Mr. Brightside")
        self.assertEqual(media.spoken_title({"title": "Song Name ft. Someone Else"}), "Song Name")
        self.assertEqual(media.spoken_title({"title": "Cat falling off a table."}), "Cat falling off a table")
        self.assertEqual(media.spoken_title({"title": "lofi hip hop radio 📚 beats to relax/study to"}),
                         "lofi hip hop radio beats to relax study to")

    def test_best_skips_live_and_long_mixes(self):
        results = [{"id": "a", "duration": None}, {"id": "b", "duration": 3 * 3600}, {"id": "c", "duration": 240}]
        self.assertEqual(media.best(results)["id"], "c")


if __name__ == "__main__":
    unittest.main()
