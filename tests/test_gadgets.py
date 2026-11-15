import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import gadgets


class GadgetCardTest(unittest.TestCase):
    def test_card_shows_number_name_and_description(self):
        svg = gadgets.render_card(1, gadgets.GADGETS[0])
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn(">01</text>", svg)
        self.assertIn("未来ガジェット 1号機", svg)
        self.assertIn("Cursor Board", svg)
        self.assertIn(gadgets.GADGETS[0]["desc"], svg)

    def test_card_escapes_text(self):
        svg = gadgets.render_card(1, {"slug": "x", "name": "<x>", "desc": "a & b", "language": "Go"})
        self.assertNotIn("<x>", svg)
        self.assertIn("a &amp; b", svg)

    def test_render_all_writes_one_file_per_gadget(self):
        out = Path(tempfile.mkdtemp())
        try:
            paths = gadgets.render_all(out)
            self.assertEqual([p.name for p in paths], [
                gadgets.card_filename(i, g) for i, g in enumerate(gadgets.GADGETS, start=1)
            ])
        finally:
            shutil.rmtree(out)


if __name__ == "__main__":
    unittest.main()
