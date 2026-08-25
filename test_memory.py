import tempfile
import unittest
from pathlib import Path

from memory import Memory


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.memory = Memory(Path(self.tempdir.name) / "memory.sqlite3")

    def tearDown(self):
        self.memory.close()
        self.tempdir.cleanup()

    def test_fact_lifecycle(self):
        fact_id = self.memory.remember("the user uses PrusaSlicer")
        self.assertEqual(self.memory.facts(), [(fact_id, "the user uses PrusaSlicer")])
        self.assertEqual(self.memory.remember("owner uses prusaslicer"), fact_id)
        self.assertTrue(self.memory.forget(fact_id))
        self.assertEqual(self.memory.facts(), [])

    def test_recent_is_chronological(self):
        for number in range(8):
            self.memory.record(f"question {number}", f"answer {number}")
        recent = self.memory.recent(limit=2)
        self.assertEqual([message["content"] for message in recent], ["question 6", "answer 6", "question 7", "answer 7"])

    def test_recall_skips_recent_and_finds_relevant_exchange(self):
        self.memory.record("My Voron uses ABS filament", "A sensible pairing, sir.")
        for number in range(6):
            self.memory.record(f"unrelated message {number}", "Quite.")
        recalled = self.memory.recall("What filament does my Voron use?")
        self.assertEqual(recalled, [("My Voron uses ABS filament", "A sensible pairing, sir.")])


if __name__ == "__main__":
    unittest.main()
