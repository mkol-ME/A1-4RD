import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

import markets


def event(title, volume, tags=(), description="", questions=()):
    return {"title": title, "volume": str(volume), "tags": [{"label": t} for t in tags],
            "description": description, "markets": [{"question": q} for q in questions]}


def top(query, events):
    wanted = {w for w in markets._words(query) if len(w) > 2 and w not in markets.STOP}
    ranked = markets.rank(events, wanted)
    return ranked[0]["title"] if ranked else None


# Each case is a real search result set, trimmed, from the day this was written.
# Every one of them went wrong under some earlier ranking rule.
class RankingTests(unittest.TestCase):
    def test_small_side_market_does_not_beat_the_decision(self):
        events = [event("How many dissent at the October Fed meeting?", 2015),
                  event("Fed Decision in October?", 4677339)]
        self.assertEqual(top("fed october", events), "Fed Decision in October?")

    def test_the_game_not_the_season_futures(self):
        events = [event("Pro Football: 2027 Champion", 56004067, tags=["NFL", "Super Bowl"],
                        questions=["Will the Chicago Bears win the 2027 NFL league championship?"]),
                  event("Vikings vs. Bears", 57627, tags=["NFL"])]
        self.assertEqual(top("bears vikings", events), "Vikings vs. Bears")
        self.assertEqual(top("bears", events), "Vikings vs. Bears")

    def test_super_bowl_is_a_tag_not_a_title(self):
        events = [event("Pro Football: 2027 Champion", 56004067, tags=["NFL", "Super Bowl"]),
                  event("Who will perform at the 2027 Big Game halftime show?", 13019,
                        tags=["Music", "Super Bowl"], description="The Super Bowl halftime show...")]
        self.assertEqual(top("super bowl", events), "Pro Football: 2027 Champion")

    def test_the_fight_not_the_title_futures_that_mention_both_fighters(self):
        events = [event("UFC 331: Alexandre Pantoja vs. Joshua Van (Flyweight, Main Card)", 27914, tags=["UFC"]),
                  event("Who will be UFC Flyweight champion at the end of 2026?", 1186316, tags=["UFC"],
                        questions=["Will Joshua Van be the UFC Flyweight Champion?",
                                   "Will Alexandre Pantoja be the UFC Flyweight Champion?"])]
        self.assertEqual(top("pantoja van", events),
                         "UFC 331: Alexandre Pantoja vs. Joshua Van (Flyweight, Main Card)")

    def test_unrelated_results_are_dropped(self):
        events = [event("Who will die in The Witcher: Season 5?", 34000, tags=["TV"])]
        self.assertIsNone(top("who is favored in the bears game", events))


class PriceTests(unittest.TestCase):
    def test_placeholder_market_is_not_live(self):
        placeholder = {"active": False, "archived": True, "closed": False, "outcomePrices": '["0.49", "0.51"]',
                       "lastTradePrice": None, "bestBid": None}
        self.assertFalse(markets.live(placeholder))

    def test_midpoint_used_only_for_a_tight_book(self):
        tight = {"outcomePrices": '["0.40", "0.60"]', "bestBid": 0.45, "bestAsk": 0.46}
        wide = {"outcomePrices": '["0.38", "0.62"]', "bestBid": 0.26, "bestAsk": 0.50}
        self.assertAlmostEqual(markets.price(tight)[0], 0.455)
        self.assertAlmostEqual(markets.price(wide)[0], 0.38)

    def test_date_ladders_keep_date_order(self):
        labels = ["July 2027 Meeting", "January 2027 Meeting", "October 2026 Meeting", "April 2027 Meeting"]
        self.assertEqual(sorted(labels, key=markets.date_order),
                         ["October 2026 Meeting", "January 2027 Meeting", "April 2027 Meeting", "July 2027 Meeting"])


if __name__ == "__main__":
    unittest.main()
