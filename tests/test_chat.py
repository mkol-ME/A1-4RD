"""How the text client lays out reply frames, without a server."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "client"))

import chat


def render(*turns: list) -> str:
    out = []
    screen = chat.Screen(out.append)
    for frames in turns:
        for frame in frames:
            screen.show(frame)
        screen.finish()
    return "".join(out)


class Layout(unittest.TestCase):
    def test_sentences_run_on_as_one_paragraph(self):
        self.assertEqual(render([{"text": "Forty minutes, sir."}, {"text": "The bed is still warm."}]),
                         "Alfred: Forty minutes, sir. The bed is still warm.\n")

    def test_a_given_reply_is_one_sentence_to_a_line(self):
        self.assertEqual(render([{"text": "Three results.", "line": True},
                                 {"text": "First one.", "line": True},
                                 {"text": "Second one.", "line": True}]),
                         "Alfred: Three results.\n"
                         "        First one.\n"
                         "        Second one.\n")

    def test_holding_line_sits_above_the_answer(self):
        self.assertEqual(render([{"holding": "One moment."}, {"text": "It rained."}]),
                         "(One moment.)\nAlfred: It rained.\n")

    def test_media_is_a_link_under_the_announcement(self):
        self.assertEqual(render([{"text": "Playing it now.", "line": True},
                                 {"media": {"id": "abc123", "title": "A Video", "start": 95.4}}]),
                         "Alfred: Playing it now.\n"
                         "        > A Video  https://youtu.be/abc123?t=95\n")

    def test_each_turn_gets_its_own_label(self):
        self.assertEqual(render([{"text": "Yes."}], [{"text": "No."}]),
                         "Alfred: Yes.\nAlfred: No.\n")

    def test_no_colour_codes_when_colour_is_off(self):
        self.assertNotIn("\033", render([{"holding": "Hm."}, {"text": "Done."}]))


if __name__ == "__main__":
    unittest.main()
