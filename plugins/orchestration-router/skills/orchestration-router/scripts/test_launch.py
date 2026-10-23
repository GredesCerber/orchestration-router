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


class WaitTests(unittest.TestCase):
    def run_dir(self, final_text):
        d = Path(tempfile.mkdtemp())
        (d / "run.json").write_text('{"task_id": "t1", "engine": "codex", "pid": 4242}', encoding="utf-8")
        (d / "last.txt").write_text(final_text, encoding="utf-8")
        return d

    def test_returns_when_worker_exits(self):
        d = self.run_dir("Вызов → Осмысление → Рефлексия")
        with mock.patch("launch.alive", side_effect=[True, False]), \
                mock.patch("launch.time.sleep"), mock.patch("builtins.print") as out:
            code = launch.wait(SimpleNamespace(run_dir=str(d), timeout=60, interval=1))
        self.assertEqual(code, 0)
        self.assertIn('"timed_out": false', out.call_args[0][0])

    def test_timeout_reports_running(self):
        d = self.run_dir("")
        with mock.patch("launch.alive", return_value=True), mock.patch("launch.time.sleep"), \
                mock.patch("launch.time.monotonic", side_effect=[0, 0, 100, 100]), \
                mock.patch("builtins.print"):
            self.assertEqual(launch.wait(SimpleNamespace(run_dir=str(d), timeout=50, interval=1)), 3)


if __name__ == "__main__":
    unittest.main()
