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
                         "Não entendi, senhor.", "Pode repetir o que disse?", "Está tudo certo por aqui."):
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
        self.assertEqual(ration.apply("Good evening, Bruce."), "Good evening, Bruce.")
        self.assertEqual(ration.apply("Entendido, senhor."), "Entendido.")

    def test_first_turn_may_use_it(self):
        self.assertEqual(spoken.TitleRation([]).apply("Evening, sir."), "Evening, sir.")


class Address(unittest.TestCase):
    def test_the_commands(self):
        for prompt, title in (("use ma'am responses", "ma'am"), ("Alfred, use ma’am responses.", "ma'am"),
                              ("use maam responses", "ma'am"), ("use madam responses", "madam"),
                              ("use sir responses", "sir"), ("sir mode", "sir"), ("call me ma'am", "ma'am"),
                              ("address me as madam please", "madam"), ("use female responses", "ma'am"),
                              ("use male responses", "sir"), ("me chame de senhora", "ma'am")):
            self.assertEqual(spoken.address_command(prompt), title, prompt)

    def test_the_bare_title(self):
        # What he actually said, 2026-09-24: none of these had "responses" after them.
        for prompt, title in (("alfred use maam", "ma'am"), ("use maam", "ma'am"), ("switch to maam", "ma'am"),
                              ("switch back to sir", "sir"), ("Use ma'am, please.", "ma'am"),
                              ("go back to sir", "sir"), ("use madam instead", "madam")):
            self.assertEqual(spoken.address_command(prompt), title, prompt)

    def test_mentions_are_not_commands(self):
        for prompt in ("the sir responses were funny", "why do you call me sir", "use the printer",
                       "call me later", "what does ma'am mean", "use sensible responses",
                       "use female", "switch to spotify", "go to madame tussauds", "use maam when my mom visits"):
            self.assertIsNone(spoken.address_command(prompt), prompt)

    def test_every_position_takes_the_title(self):
        ration = spoken.TitleRation([], "ma'am")
        self.assertEqual(ration.apply("Sir."), "Ma'am.")
        self.assertEqual(ration.apply("That's a myth, sir."), "That's a myth, ma'am.")
        self.assertEqual(spoken.TitleRation([], "madam").apply("Sir, you should see a doctor."),
                         "Madam, you should see a doctor.")

    def test_the_ration_counts_any_title(self):
        self.assertEqual(spoken.TitleRation(["They aren't, ma'am."], "ma'am").apply("Fine, sir."), "Fine.")
        self.assertEqual(spoken.TitleRation(["Dogs.", "Cats."], "ma'am").apply("Fine, ma'am."), "Fine, ma'am.")

    def test_switching_back_undoes_the_old_title(self):
        # The history he imitates still says "ma'am" for a turn or two after the switch.
        self.assertEqual(spoken.TitleRation([], "sir").apply("Fine, ma'am."), "Fine, sir.")
        self.assertEqual(spoken.TitleRation([], "sir").apply("A senhora já decidiu."), "O senhor já decidiu.")

    def test_portuguese_articles_agree(self):
        ration = spoken.TitleRation(["Não."], "ma'am")
        self.assertEqual(ration.apply("O senhor já decidiu."), "A senhora já decidiu.")
        self.assertEqual(ration.apply("Isso é do senhor, e eu disse ao senhor."), "Isso é da senhora, e eu disse à senhora.")
        self.assertEqual(spoken.TitleRation([], "ma'am").apply("Entendido, senhor."), "Entendido, senhora.")

    def test_names_are_left_alone(self):
        ration = spoken.TitleRation([], "ma'am")
        self.assertEqual(ration.apply("Sir Isaac Newton said so, sir."), "Sir Isaac Newton said so, ma'am.")
        self.assertEqual(spoken.TitleRation([], "sir").apply("Madam Curie."), "Madam Curie.")


if __name__ == "__main__":
    unittest.main()
