import unittest
from datetime import datetime, timedelta, timezone

from scripts import worldline


def _state(**overrides):
    state = worldline.initial_state()
    state.update(overrides)
    return state


class ParseTitleTest(unittest.TestCase):
    def test_accepts_common_spellings(self):
        for title in ("D-Mail: hello", "d-mail:hello", "DMail : hello", "D-Mail：hello"):
            with self.subTest(title=title):
                self.assertEqual(worldline.parse_title(title), "hello")

    def test_rejects_non_dmail_titles(self):
        self.assertIsNone(worldline.parse_title("Bug report"))
        self.assertIsNone(worldline.parse_title("Re: D-Mail: hello"))

    def test_strips_whitespace(self):
        self.assertEqual(worldline.parse_title("D-Mail:   El Psy Kongroo   "), "El Psy Kongroo")


class TruncateBytesTest(unittest.TestCase):
    def test_keeps_short_text(self):
        self.assertEqual(worldline.truncate_bytes("hello"), "hello")

    def test_cuts_ascii_at_limit(self):
        self.assertEqual(len(worldline.truncate_bytes("a" * 50).encode("utf-8")), 36)

    def test_never_splits_multibyte_characters(self):
        text = "世界線" * 10
        result = worldline.truncate_bytes(text)
        self.assertLessEqual(len(result.encode("utf-8")), 36)
        self.assertEqual(result, "世界線" * 4)


class DivergenceTest(unittest.TestCase):
    def test_is_deterministic(self):
        self.assertEqual(worldline.divergence_for("seed"), worldline.divergence_for("seed"))

    def test_values_stay_inside_their_field(self):
        ranges = {
            "alpha": (0.3, 0.7),
            "beta": (1.1, 1.14),
            "gamma": (2.6, 2.7),
        }
        seen = set()
        for i in range(3000):
            value, field = worldline.divergence_for(f"seed-{i}")
            seen.add(field)
            self.assertRegex(value, r"^\d\.\d{6}$")
            if field == "steins_gate":
                self.assertEqual(value, worldline.STEINS_GATE)
            else:
                low, high = ranges[field]
                self.assertTrue(low <= float(value) < high, (value, field))
        self.assertEqual(seen, {"alpha", "beta", "gamma", "steins_gate"})


class ProcessTest(unittest.TestCase):
    NOW = datetime(2026, 11, 15, 2, 0, tzinfo=timezone.utc)

    def _send(self, state, title="D-Mail: hello", sender="okabe", number=1, at=None):
        return worldline.process(state, title, sender, number, at or self.NOW)

    def test_accepted_dmail_shifts_worldline_and_records_history(self):
        state, result = self._send(_state())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["from"], "0.571024")
        self.assertEqual(result["to"], state["divergence"])
        entry = state["history"][0]
        self.assertEqual(entry["sender"], "okabe")
        self.assertEqual(entry["message"], "hello")
        self.assertEqual(entry["from"], "0.571024")

    def test_empty_message_is_rejected_without_changing_state(self):
        original = _state()
        state, result = self._send(original, title="D-Mail:   ")
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "empty")
        self.assertEqual(state, original)

    def test_non_dmail_title_is_rejected(self):
        _, result = self._send(_state(), title="hello")
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "not_dmail")

    def test_same_sender_within_an_hour_is_rate_limited(self):
        state, _ = self._send(_state())
        state, result = self._send(state, number=2, at=self.NOW + timedelta(minutes=59))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "rate_limited")

    def test_same_sender_after_an_hour_is_accepted(self):
        state, _ = self._send(_state())
        _, result = self._send(state, number=2, at=self.NOW + timedelta(hours=1))
        self.assertTrue(result["accepted"])

    def test_other_sender_is_not_rate_limited(self):
        state, _ = self._send(_state())
        _, result = self._send(state, sender="daru", number=2, at=self.NOW + timedelta(minutes=1))
        self.assertTrue(result["accepted"])

    def test_history_keeps_newest_five(self):
        state = _state()
        for i in range(7):
            state, _ = self._send(state, sender=f"user{i}", number=i, title=f"D-Mail: msg{i}")
        self.assertEqual([e["message"] for e in state["history"]], ["msg6", "msg5", "msg4", "msg3", "msg2"])

    def test_long_message_is_truncated_to_36_bytes(self):
        state, result = self._send(_state(), title="D-Mail: " + "x" * 80)
        self.assertTrue(result["accepted"])
        self.assertEqual(len(state["history"][0]["message"]), 36)


class RenderingTest(unittest.TestCase):
    def test_escape_neutralises_markup_and_mentions(self):
        escaped = worldline.escape_inline("<img src=x>|[link](u)`@kurisu")
        for raw in ("<", ">", "|", "[", "`", "@"):
            self.assertNotIn(raw, escaped)

    def test_history_table_lists_entries(self):
        state, _ = worldline.process(_state(), "D-Mail: hi|there", "okabe", 1, ProcessTest.NOW)
        table = worldline.render_history(state["history"])
        self.assertIn("okabe", table)
        self.assertIn("hi&#124;there", table)

    def test_history_placeholder_when_empty(self):
        self.assertIn("No D-Mail", worldline.render_history([]))

    def test_replace_block_only_touches_marked_region(self):
        text = "head\n<!-- X:START -->\nold\n<!-- X:END -->\ntail"
        result = worldline.replace_block(text, "X", "new")
        self.assertEqual(result, "head\n<!-- X:START -->\nnew\n<!-- X:END -->\ntail")

    def test_replace_block_requires_markers(self):
        with self.assertRaises(ValueError):
            worldline.replace_block("no markers", "X", "new")

    def test_svg_shows_every_digit(self):
        svg = worldline.render_svg("1.048596", "steins_gate")
        self.assertTrue(svg.startswith("<svg"))
        for ch in "1048596":
            self.assertIn(f">{ch}</text>", svg)
        self.assertIn("STEINS;GATE", svg)

    def test_svg_label_keeps_greek_letter(self):
        self.assertIn("β ATTRACTOR FIELD", worldline.render_svg("1.130205", "beta"))


if __name__ == "__main__":
    unittest.main()
