"""Picking a YouTube channel by a misheard name, and finding its uploads on a topic."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

import youtube

# As YouTube's channel search returned them on 2026-09-17.
MANZEL = [
    {"id": "UCGHNXD_xKIEc2RzfmIM1rUg", "name": "Money Manzel MMA", "followers": 19000},
    {"id": "UCAELXX1-cUSA5Lc7aDFMZsw", "name": "TonyHasDiedMMA", "followers": 25200},
    {"id": "UCGeBogGDZ9W3dsGx-mWQGJA", "name": "IMPAULSIVE", "followers": 4820000},
]
BEDTIME = [
    {"id": "UCQAMRRo7fPbQMzlJWOexlZg", "name": "Bedtime MMA", "followers": 134000},
    {"id": "UCNceF97kvrOKX-hhGwyxJdw", "name": "Bedtime MMA", "followers": 4},
    {"id": "UCOy0foWJiEemp_vIEuaRJLQ", "name": "Bedtime MMA Clips", "followers": 13},
]
GURU = [
    {"id": "UCIhQvpinmS8Eq6PrQ021DKQ", "name": "THE MMA GURU", "followers": 453000},
    {"id": "UCENL5Z7UGq-10GvlsIeJSXA", "name": "grayshirt108", "followers": 16300},
    {"id": "UCE-gv6zO4Qo6AAZiLvuVN3w", "name": "The MMA Guru", "followers": 2570},
]
UPLOADS = [
    {"id": "aaaaaaaaaaa", "title": "Silva vs Delgado Immediate Reaction"},
    {"id": "bbbbbbbbbbb", "title": "UFC 331 Full Card Predictions (BEDTIME BICKS)"},
    {"id": "ccccccccccc", "title": "UFC 330 Full Card Predictions"},
    {"id": "ddddddddddd", "title": "UFC 331 Main Event Breakdown"},
]


class BestChannel(unittest.TestCase):
    def test_misheard_spelling_still_finds_it(self):
        self.assertEqual(youtube.best_channel("money manzell mma", MANZEL)["name"], "Money Manzel MMA")
        self.assertEqual(youtube.best_channel("moneymanzellmma", MANZEL)["name"], "Money Manzel MMA")

    def test_namesakes_go_to_the_real_one(self):
        self.assertEqual(youtube.best_channel("bedtime mma", BEDTIME)["followers"], 134000)
        self.assertEqual(youtube.best_channel("the mma guru", GURU)["followers"], 453000)

    def test_exact_name_with_no_audience_loses_to_the_real_channel(self):
        lucas = [
            {"id": "UC7LzaJA-R2E52qzd5GW-kpg", "name": "LucasTracyMMA", "followers": 168000},
            {"id": "UCo_nhuiHE5OHu0pK-WCVISQ", "name": "Peaches and Creamville", "followers": 5640},
            {"id": "UCHMHPzhaPB_2Ay_SakYWC_Q", "name": "lucas tracy", "followers": 1},
        ]
        self.assertEqual(youtube.best_channel("lucas tracy", lucas)["name"], "LucasTracyMMA")

    def test_nothing_close_is_none(self):
        self.assertIsNone(youtube.best_channel("lucas tracy", MANZEL))


class Matching(unittest.TestCase):
    def test_card_number_must_match_exactly(self):
        titles = [u["title"] for u in youtube.matching(UPLOADS, "ufc 331 predictions")]
        self.assertEqual(titles, ["UFC 331 Full Card Predictions (BEDTIME BICKS)", "UFC 331 Main Event Breakdown"])

    def test_no_match_is_empty(self):
        self.assertEqual(youtube.matching(UPLOADS, "ufc 340"), [])


if __name__ == "__main__":
    unittest.main()
