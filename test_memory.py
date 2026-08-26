import tempfile
import unittest
from pathlib import Path

from memory import Memory, local_time_reply, now_line


class MemoryTests(unittest.TestCase):
    def test_clock_instruction_uses_normal_numeric_time(self):
        line = now_line()
        self.assertRegex(line, r"\b(?:1[0-2]|[1-9]):[0-5][0-9] [AP]M\b")
        self.assertIn("reply only", line)
        self.assertIn("normal numeric format", line)

    def test_fast_clock_reply_is_short_and_numeric(self):
        self.assertRegex(local_time_reply(), r"^(?:1[0-2]|[1-9]):[0-5][0-9] [AP]M, sir\.$")

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

    def test_recent_drops_a_stale_conversation(self):
        """Last night is not this morning's conversation."""
        self.memory.record("what time is it", "It is past midnight, sir.")
        self.memory.db.execute(
            "UPDATE exchanges SET created_at = datetime('now', '-10 hours')")
        self.memory.db.commit()
        self.assertEqual(self.memory.recent(), [])
        self.memory.record("morning alfred", "Good morning, sir.")
        self.assertEqual([m["content"] for m in self.memory.recent()],
                         ["morning alfred", "Good morning, sir."])

    def test_recent_is_chronological(self):
        for number in range(8):
            self.memory.record(f"question {number}", f"answer {number}")
        recent = self.memory.recent(limit=2)
        self.assertEqual([message["content"] for message in recent], ["question 6", "answer 6", "question 7", "answer 7"])

    def test_recall_skips_recent_and_finds_what_owner_said(self):
        self.memory.record("My Voron uses ABS filament", "A sensible pairing, sir.")
        for number in range(6):
            self.memory.record(f"unrelated message {number}", "Quite.")
        recalled = self.memory.recall("What filament does my Voron use?")
        self.assertEqual(recalled, ["My Voron uses ABS filament"])

    def test_his_own_replies_are_never_recalled(self):
        """The loop this closes: a wrong answer must not become its own evidence."""
        self.memory.record("what time is it", "It is past midnight, sir.")
        for number in range(6):
            self.memory.record(f"unrelated message {number}", "Quite.")
        for query in ("is it past midnight", "what time is it", "midnight"):
            for line in self.memory.recall(query):
                self.assertNotIn("past midnight", line.lower(), query)

    def test_replies_are_still_stored_in_full(self):
        """Unsearchable is not the same as discarded — the record stays complete."""
        self.memory.record("my printer is a bambu", "Noted, sir.")
        stored = self.memory.db.execute(
            "SELECT assistant_text FROM exchanges ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(stored[0], "Noted, sir.")


if __name__ == "__main__":
    unittest.main()
