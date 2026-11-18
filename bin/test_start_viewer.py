import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class MonitorSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.viewer = self.directory / "viewer"
        self.viewer.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" >> \"$CALLS\"\n"
            "if [ \"$1\" = /list:monitor ]; then\n"
            "  echo '1: primary; 2: secondary'\n"
            "  exit \"${LIST_STATUS:-255}\"\n"
            "fi\n"
        )
        self.viewer.chmod(0o755)
        self.calls = self.directory / "calls"
        self.launcher = self.directory / "ww-start-viewer.sh"
        self.launcher.write_text(
            Path(__file__).with_name("ww-start-viewer.sh").read_text().replace(
                "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                str(self.directory / "unavailable-powershell"),
            )
        )
        self.environment = {
            **os.environ,
            "WEASELWAY_VIEWER": str(self.viewer),
            "CALLS": str(self.calls),
        }

    def launch(self, option, answer=""):
        return subprocess.run(
            ["bash", str(self.launcher), option],
            input=answer,
            text=True,
            capture_output=True,
            env=self.environment,
        )

    def test_list_does_not_connect(self):
        result = self.launch("--list-monitors")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("secondary", result.stdout)
        self.assertEqual(self.calls.read_text(), "/list:monitor\n")

    def test_list_failure_is_reported(self):
        self.environment["LIST_STATUS"] = "7"
        result = self.launch("--select-monitors", "1,2\n")
        self.assertEqual(result.returncode, 7)
        self.assertNotIn("Monitor IDs", result.stderr)

    def test_empty_selection_cancels(self):
        result = self.launch("--select-monitors", "\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cancelled", result.stderr)
        self.assertEqual(self.calls.read_text(), "/list:monitor\n")

    def test_invalid_selection_does_not_connect(self):
        result = self.launch("--select-monitors", "1;invalid\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("error:", result.stderr)
        self.assertEqual(self.calls.read_text(), "/list:monitor\n")

    def test_end_of_input_cancels(self):
        result = self.launch("--select-monitors")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cancelled", result.stderr)
        self.assertEqual(self.calls.read_text(), "/list:monitor\n")

    def test_selection_forwards_ids_in_order(self):
        for name, body in {
            "systemctl": "echo WEASELWAY_VSOCK_PORT=1234\n",
            "wslinfo": "echo test-vm\n",
        }.items():
            path = self.directory / name
            path.write_text("#!/bin/sh\n" + body)
            path.chmod(0o755)
        self.environment.update(
            PATH=str(self.directory) + os.pathsep + os.environ["PATH"],
            DEBUG="1",
        )
        result = self.launch("--select-monitors", "2,1\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/multimon\n/monitors:2,1\n", self.calls.read_text())


if __name__ == "__main__":
    unittest.main()
