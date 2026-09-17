"""What Alfred says aloud: which voice reads it, and how often he says "sir"."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

import spoken


class LooksPortuguese(unittest.TestCase):
    def test_the_replies_his_english_voice_mangled(self):
        # Both from 2026-09-17, read out by the English voice.
        for sentence in ("Entendido, senhor.", "Se preferir assim, continuaremos em português.",
                         "Não entendi, senhor.", "Pode repetir o que disse?", "Tudo em ordem por aqui."):
            self.assertTrue(spoken.looks_portuguese(sentence), sentence)

    def test_english_stays_english(self):
        for sentence in ("They aren't, sir.", "Do what you must.", "No, as I said, the café is shut.",
                         "Um, I'd get a second opinion.", "Peer pressure is a poor excuse for kidney failure, sir.",
                         "Playing Waka Waka by Shakira."):
            self.assertFalse(spoken.looks_portuguese(sentence), sentence)


class TitleRation(unittest.TestCase):
    def test_once_per_reply(self):
        ration = spoken.TitleRation(["Two hundred and six.", "Dogs. They appreciate company."])
        self.assertEqual(ration.apply("That's a myth, sir."), "That's a myth, sir.")
        self.assertEqual(ration.apply("Documentaries can be wrong, sir."), "Documentaries can be wrong.")

    def test_not_within_two_replies(self):
        self.assertEqual(spoken.TitleRation(["They aren't, sir."]).apply("They see just fine, sir."),
                         "They see just fine.")
        self.assertEqual(spoken.TitleRation(["They aren't, sir.", "Dogs."]).apply("On what, sir?"), "On what?")
        self.assertEqual(spoken.TitleRation(["They aren't, sir.", "Dogs.", "On what?"]).apply("Fine, sir."),
                         "Fine, sir.")

    def test_every_position_reads_cleanly(self):
        ration = spoken.TitleRation(["On what, sir?"])
        self.assertEqual(ration.apply("Sir, you should see a doctor."), "You should see a doctor.")
        self.assertEqual(ration.apply("Yes, sir, I did."), "Yes, I did.")
        self.assertEqual(ration.apply("On what, sir?"), "On what?")
        self.assertEqual(ration.apply("Go to a doctor, sir!"), "Go to a doctor!")

    def test_what_is_left_alone(self):
        ration = spoken.TitleRation(["Não, senhor."])
        self.assertEqual(ration.apply("Sir."), "Sir.")
        self.assertEqual(ration.apply("O senhor já decidiu."), "O senhor já decidiu.")
        self.assertEqual(ration.apply("Good evening, the user."), "Good evening, the user.")
        self.assertEqual(ration.apply("Entendido, senhor."), "Entendido.")

    def test_first_turn_may_use_it(self):
        self.assertEqual(spoken.TitleRation([]).apply("Morning, sir."), "Morning, sir.")


if __name__ == "__main__":
    unittest.main()
