import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

import guru

CHAPTERS = [
    {"start": 0, "end": 112, "title": "<Untitled Chapter 1>"},
    {"start": 1122, "end": 1262, "title": "Tim Elliott vs Edgar Chairez"},
    {"start": 1680, "end": 1793, "title": "Manon Fiorot vs Alexa Grasso"},
    {"start": 2276, "end": 2510, "title": "Brandon Moreno vs Joseph Morales"},
    {"start": 2510, "end": 3032, "title": "Jean Silva vs Jose Miguel Delgado"},
]


class ParseTests(unittest.TestCase):
    def test_questions(self):
        cases = {
            "who does the guru pick in silva delgado": ("ask", "predictions", "silva delgado"),
            "what did the MMA Guru say about Moreno vs Morales?": ("ask", None, "moreno morales"),
            "what does the guru think about aspinall": ("ask", None, "aspinall"),
            "whats the gurus prediction for pantoja van": ("ask", "predictions", "pantoja van"),
            "how did the guru react to the grasso fight": ("ask", "recap", "grasso"),
        }
        for prompt, (action, kind, subject) in cases.items():
            request = guru.parse(prompt)
            self.assertEqual((request["action"], request["kind"], request["subject"]), (action, kind, subject), prompt)

    def test_play_requests(self):
        request = guru.parse("play the guru's breakdown of the grasso fiorot fight")
        self.assertEqual((request["action"], request["subject"]), ("play", "grasso fiorot"))
        request = guru.parse("play the gurus latest recap")
        self.assertEqual((request["action"], request["kind"], request["subject"]), ("play", "recap", ""))
        self.assertEqual(guru.parse("play that part", have_last=True), {"action": "play_last"})
        self.assertIsNone(guru.parse("play that part"))

    def test_not_about_him(self):
        for prompt in ("play bohemian rhapsody", "who won the ufc fight", "whats the weather"):
            self.assertIsNone(guru.parse(prompt), prompt)


class SectionTests(unittest.TestCase):
    def test_chapter_by_names_with_accents_and_order(self):
        self.assertEqual(guru.match_chapter(CHAPTERS, "delgado silva")["start"], 2510)
        self.assertEqual(guru.match_chapter(CHAPTERS, "chairez")["title"], "Tim Elliott vs Edgar Chairez")
        self.assertEqual(guru.match_chapter(CHAPTERS, "cháirez")["start"], 1122)
        self.assertIsNone(guru.match_chapter(CHAPTERS, "pantoja van"))

    def test_captions_fallback_finds_the_densest_stretch(self):
        captions = [[10, "welcome back"], [400, "aspinall mentioned once"]]
        captions += [[900 + i * 20, f"aspinall line {i}"] for i in range(8)]
        section = guru.match_captions(captions, "aspinall")
        self.assertEqual(section["start"], 880)
        self.assertEqual(section["end"], 900 + 7 * 20 + 45)

    def test_excerpt_is_the_section_only(self):
        captions = [[100, "before"], [2510, "to the main event"], [2600, "silva wins"], [3100, "after"]]
        self.assertEqual(guru.excerpt(captions, 2510, 3032), "to the main event silva wins")

    def test_clip_frame(self):
        found = {"video": {"id": "mqrbRyXHTAU", "title": "Predictions", "duration": 3032},
                 "section": CHAPTERS[-1], "commentator": "The MMA Guru"}
        self.assertEqual(guru.clip(found), {"id": "mqrbRyXHTAU", "title": "The MMA Guru on Jean Silva vs Jose Miguel Delgado",
                                            "duration": 3032, "start": 2510, "end": 3032})


if __name__ == "__main__":
    unittest.main()


class CardTests(unittest.TestCase):
    UPLOADS = [
        {"id": "aaaaaaaaaaa", "title": "UFC Noche Event Recap Silva vs Delgado Full Card Reaction & Breakdown"},
        {"id": "bbbbbbbbbbb", "title": "UFC 331 Predictions & Full Card Breakdown"},
        {"id": "ccccccccccc", "title": "UFC 330 Predictions & Full Card Breakdown"},
    ]

    def test_the_question_that_found_nothing(self):
        # 2026-09-17, as Whisper delivered it.
        request = guru.parse("has mma guru released a prediction post for ufc 331")
        self.assertEqual((request["kind"], request["subject"]), ("predictions", "ufc 331"))
        self.assertEqual(guru.match_card(self.UPLOADS, request["subject"])["id"], "bbbbbbbbbbb")

    def test_wrong_number_or_no_card(self):
        self.assertIsNone(guru.match_card(self.UPLOADS, "ufc 332"))
        self.assertIsNone(guru.match_card(self.UPLOADS, "silva delgado"))
