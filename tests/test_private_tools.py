"""Loading tools from outside the repository, and surviving the ones that are broken."""

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

import private_tools

GOOD = '''
TOOLS = [{"type": "function", "function": {"name": "stopwatch", "description": "x",
          "parameters": {"type": "object", "properties": {}}}}]

def dispatch(name, arguments, prompt):
    return {"ok": True, "heard": prompt, "arguments": arguments, "direct": "Lap one."}
'''


def folder(**files) -> Path:
    where = Path(tempfile.mkdtemp())
    for name, body in files.items():
        (where / f"{name}.py").write_text(textwrap.dedent(body), encoding="utf-8")
    return where


class PrivateTools(unittest.TestCase):
    def test_no_folder_means_no_tools(self):
        registry = private_tools.Registry(Path(tempfile.mkdtemp()) / "absent")
        self.assertEqual(registry.schemas(), [])
        self.assertFalse(registry.owns("stopwatch"))

    def test_loads_and_passes_his_own_words_through(self):
        registry = private_tools.Registry(folder(clock=GOOD))
        self.assertEqual([s["function"]["name"] for s in registry.schemas()], ["stopwatch"])
        result = registry.dispatch("stopwatch", {"lap": 1}, "start the stopwatch please")
        self.assertEqual(result["heard"], "start the stopwatch please")
        self.assertEqual(result["direct"], "Lap one.")

    def test_a_broken_module_costs_only_itself(self):
        registry = private_tools.Registry(folder(clock=GOOD, broken="def dispatch(:\n"))
        self.assertTrue(registry.owns("stopwatch"))
        self.assertIn("broken.py", [file for file, _ in registry.problems])

    def test_a_module_without_dispatch_is_refused(self):
        registry = private_tools.Registry(folder(half="TOOLS = []\n"))
        self.assertEqual(registry.schemas(), [])
        self.assertIn("half.py", [file for file, _ in registry.problems])

    def test_may_not_take_over_a_built_in(self):
        registry = private_tools.Registry(folder(clock=GOOD), reserved={"stopwatch"})
        self.assertFalse(registry.owns("stopwatch"))

    def test_a_raising_tool_never_raises(self):
        registry = private_tools.Registry(folder(clock=GOOD.replace(
            'return {"ok": True', 'raise RuntimeError("jammed")\n    return {"ok": True')))
        result = registry.dispatch("stopwatch", {}, "")
        self.assertFalse(result["ok"])
        self.assertIn("jammed", result["error"])

    def test_a_non_dict_answer_is_turned_into_an_error(self):
        registry = private_tools.Registry(folder(clock=GOOD.replace(
            'return {"ok": True, "heard": prompt, "arguments": arguments, "direct": "Lap one."}',
            'return "Lap one."')))
        self.assertFalse(registry.dispatch("stopwatch", {}, "")["ok"])


if __name__ == "__main__":
    unittest.main()
