import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

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

    def test_opening_leaves_no_write_lock_behind(self):
        # A second opener is what a maintenance script is while the voice server runs.
        self.memory.close()
        self.memory = Memory(Path(self.tempdir.name) / "memory.sqlite3")
        self.assertFalse(self.memory.db.in_transaction)
        other = Memory(Path(self.tempdir.name) / "memory.sqlite3")
        try:
            self.assertFalse(other.db.in_transaction)
            other.remember("a second connection can write")
        finally:
            other.close()

    def test_fact_lifecycle(self):
        fact_id = self.memory.remember("Bruce uses PrusaSlicer")
        self.assertEqual(self.memory.facts(), [(fact_id, "Bruce uses PrusaSlicer")])
        self.assertEqual(self.memory.remember("bruce uses prusaslicer"), fact_id)
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

    def test_recall_skips_recent_and_finds_what_the_owner_said(self):
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


class ToolGateTests(unittest.TestCase):
    """Which spoken turns pay for the tool decider before he answers."""

    def test_opinions_and_questions_about_him_skip_the_decider(self):
        import memory_tools
        for prompt in ("what do you think about my new printer", "what do you think of petg",
                       "are you awake", "are you sure about that"):
            self.assertFalse(memory_tools.may_need_tools(prompt), prompt)

    def test_lookups_still_reach_it(self):
        import memory_tools
        for prompt in ("do you think it will rain today", "is it worth buying a bambu x1c",
                       "do you remember what i said about my cousin", "what temperature should i run petg at",
                       "what did i tell you about my guitar lessons", "remember that my printer is a bambu p1s",
                       "what do you remember about my housemate"):
            self.assertTrue(memory_tools.may_need_tools(prompt), prompt)

    def test_complete_questions_are_decided_without_the_conversation(self):
        import memory_tools
        for prompt in ("what should i have for dinner tonight", "what temperature should i run petg at",
                       "what did i tell you about my guitar lessons", "how many feet are in a mile",
                       "who won the ufc fight last night"):
            self.assertTrue(memory_tools.stands_alone(prompt), prompt)

    def test_worth_recalling_skips_the_rote_and_the_tiny(self):
        """The gate in front of unasked recall: an embedding is cheap, not free."""
        import memory_tools
        for prompt in ("thanks alfred", "good evening", "yeah", "ok", "hello", "mm hmm"):
            self.assertFalse(memory_tools.worth_recalling(prompt), prompt)
        for prompt in ("the radiator is knocking again", "the spool still hasnt turned up",
                       "i might skip the long run this week", "nothing is going right today"):
            self.assertTrue(memory_tools.worth_recalling(prompt), prompt)

    def test_fragments_and_references_keep_it(self):
        import memory_tools
        for prompt in ("what about 48", "and tomorrow", "and the bed temperature", "is that true",
                       "which one is better", "how much does it cost", "what did you mean by that",
                       "do you think it will rain today", "what about for abs on the p1s"):
            self.assertFalse(memory_tools.stands_alone(prompt), prompt)


if __name__ == "__main__":
    unittest.main()
