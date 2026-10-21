"""Offline tests for launch.py argument building; no process is started."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import launch


def args(**changes):
    value = dict(engine="claude", role="read", task_id="t1", cwd=".", model=None, effort=None,
                 allow_tool=[], add_dir=[], worktree=False)
    value.update(changes)
    return SimpleNamespace(**value)


class BuildTests(unittest.TestCase):
    def build(self, exe="/bin/tool", **changes):
        with mock.patch("launch.shutil.which", return_value=exe):
            return launch.build(args(**changes), Path(tempfile.gettempdir()))

    def test_claude_roles(self):
        self.assertIn("plan", self.build())
        argv = self.build(role="write", allow_tool=["Bash(npm test:*)"])
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "acceptEdits")
        self.assertIn("Bash(npm test:*)", argv)

    def test_codex_sandbox_and_stdin_prompt(self):
        argv = self.build(engine="codex", effort="low")
        self.assertEqual(argv[argv.index("-s") + 1], "read-only")
        self.assertEqual(argv[-1], "-")
        self.assertIn('model_reasoning_effort="low"', argv)
        self.assertEqual(self.build(engine="codex", role="write")[self.build(
            engine="codex", role="write").index("-s") + 1], "workspace-write")

    def test_bypass_is_refused(self):
        with self.assertRaises(SystemExit):
            self.build(add_dir=["--dangerously-skip-permissions"])

    def test_batch_shim_rejects_metacharacters(self):
        with self.assertRaises(SystemExit):
            self.build(exe="C:/x/claude.cmd", role="write", allow_tool=["Bash(a & b)"])
        self.assertTrue(self.build(exe="C:/x/claude.cmd"))

    def test_missing_executable(self):
        with self.assertRaises(SystemExit):
            self.build(exe=None)


if __name__ == "__main__":
    unittest.main()
