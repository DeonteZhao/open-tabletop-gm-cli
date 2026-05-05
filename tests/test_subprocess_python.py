from __future__ import annotations

import unittest
from unittest.mock import patch

import cli
import tools


class SubprocessPythonTests(unittest.TestCase):
    def test_tool_uses_current_python_executable(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd

            class Result:
                returncode = 0
                stdout = "ok"
                stderr = ""

            return Result()

        with patch.object(tools.os.path, "exists", lambda path: True), patch.object(tools.subprocess, "run", fake_run):
            tools.execute_tool("dice", {"notation": "1d20"})

        self.assertEqual(captured["cmd"][0], tools.sys.executable)

    def test_display_push_uses_current_python_executable(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd

            class Result:
                returncode = 0
                stdout = "ok"
                stderr = ""

            return Result()

        with patch.object(cli.os.path, "exists", lambda path: True), patch.object(cli.subprocess, "run", fake_run):
            cli.push_to_display("hello")

        self.assertEqual(captured["cmd"][0], cli.sys.executable)


if __name__ == "__main__":
    unittest.main()
