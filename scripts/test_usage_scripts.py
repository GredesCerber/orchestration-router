"""Offline tests for the usage snapshot readers; synthetic data only."""
import json
import os
import tempfile
import unittest
from pathlib import Path

import claude_usage_statusline as claude
import codex_usage as codex


class ClaudeSnapshotTests(unittest.TestCase):
    def test_windows_and_remaining(self):
        snap = claude.snapshot({"rate_limits": {"five_hour": {"used_percentage": 23.5,
                                                              "resets_at": 1738425600}}})
        self.assertEqual([w["label"] for w in snap["windows"]], ["5h"])
        self.assertEqual(snap["windows"][0]["remaining_percent"], 76.5)

    def test_absent_limits_are_not_zero(self):
        self.assertEqual(claude.snapshot({})["windows"], [])
        snap = claude.snapshot({"rate_limits": {"seven_day": {"used_percentage": None}}})
        self.assertIsNone(snap["windows"][0]["remaining_percent"])


class CodexLogTests(unittest.TestCase):
    def test_last_event_wins_and_missing_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout-x.jsonl"
            events = [{"timestamp": "t1", "payload": {"rate_limits": {
                          "primary": {"used_percent": 10.0, "window_minutes": 300}}}},
                      {"timestamp": "t2", "payload": {"info": {"rate_limits": {
                          "primary": {"used_percent": 30.0, "window_minutes": 300}}}}}]
            path.write_text("\n".join(json.dumps(e) for e in events) + "\nnot json\n",
                            encoding="utf-8")
            stamp, limits = codex.last_rate_limits(path)
            self.assertEqual(stamp, "t2")
            self.assertEqual(limits["primary"]["used_percent"], 30.0)
            empty = Path(tmp) / "rollout-y.jsonl"
            empty.write_text('{"type": "other"}\n', encoding="utf-8")
            self.assertIsNone(codex.last_rate_limits(empty))


if __name__ == "__main__":
    unittest.main()
