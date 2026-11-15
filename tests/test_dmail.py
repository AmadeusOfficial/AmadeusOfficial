import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import dmail, worldline

README = """# Lab
<!-- WORLDLINE:START -->
old status
<!-- WORLDLINE:END -->
<!-- DMAIL:START -->
old log
<!-- DMAIL:END -->
"""

NOW = datetime(2026, 11, 15, 2, 0, tzinfo=timezone.utc)


class RunTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "README.md").write_text(README, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_accepted_dmail_updates_state_svg_and_readme(self):
        result, reply = dmail.run(self.root, "D-Mail: hello", "okabe", 1, NOW)

        self.assertTrue(result["accepted"])
        state = json.loads((self.root / "state" / "worldline.json").read_text(encoding="utf-8"))
        self.assertEqual(state["divergence"], result["to"])
        svg = (self.root / "assets" / "divergence-meter.svg").read_text(encoding="utf-8")
        self.assertIn(f"Divergence {result['to']}", svg)
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"`{result['to']}`", readme)
        self.assertIn("okabe", readme)
        self.assertNotIn("old log", readme)
        self.assertIn(result["to"], reply)

    def test_rejected_dmail_leaves_files_untouched(self):
        result, reply = dmail.run(self.root, "D-Mail:", "okabe", 1, NOW)

        self.assertFalse(result["accepted"])
        self.assertFalse((self.root / "state" / "worldline.json").exists())
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), README)
        self.assertIn("empty", reply)

    def test_reply_escapes_message(self):
        _, reply = dmail.run(self.root, "D-Mail: @everyone <b>", "okabe", 1, NOW)
        self.assertNotIn("@everyone", reply)
        self.assertNotIn("<b>", reply)

    def test_render_only_rebuilds_from_existing_state(self):
        dmail.render_all(self.root, worldline.initial_state())
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn("`0.571024`", readme)
        self.assertTrue((self.root / "assets" / "divergence-meter.svg").exists())


class ParseTimeTest(unittest.TestCase):
    def test_accepts_github_z_suffix(self):
        self.assertEqual(dmail.parse_time("2026-11-15T02:00:00Z"), NOW)


if __name__ == "__main__":
    unittest.main()
