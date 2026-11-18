import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_deb", HERE / "build-deb.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class DebianPackageTests(unittest.TestCase):
    def run_preinst(self, *, distribution="debian", version="13", kernel="test-WSL2", legacy=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "os-release").write_text(
                f"ID={distribution}\nVERSION_ID={version}\nPRETTY_NAME=Test\n"
            )
            (root / "uname").write_text(f"#!/bin/sh\nprintf '%s\\n' '{kernel}'\n")
            (root / "uname").chmod(0o755)
            if legacy == "symlink":
                (root / "weaselwayd").symlink_to(root / "missing")
            elif legacy:
                (root / "weaselwayd").touch()
            script = (HERE / "debian/preinst").read_text()
            script = script.replace("/etc/os-release", str(root / "os-release"))
            script = script.replace("@KERNEL@", "test-WSL2")
            script = script.replace("/usr/local/bin/weaselwayd", str(root / "weaselwayd"))
            script = script.replace("/etc/systemd/user/weaselwayd.service", str(root / "user.service"))
            script = script.replace("/etc/systemd/system/weaselway-prep.service", str(root / "prep.service"))
            return subprocess.run(
                ["sh", "-c", script, "preinst", "install"],
                env={**os.environ, "PATH": f"{root}:{os.environ['PATH']}"},
                text=True, capture_output=True,
            )

    def test_preinst_accepts_matching_debian_kernel(self):
        result = self.run_preinst()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_preinst_rejects_incompatible_targets(self):
        for kwargs, message in (
            ({"distribution": "ubuntu"}, "requires Debian 13"),
            ({"version": "12"}, "requires Debian 13"),
            ({"kernel": "other-WSL2"}, "requires WSL kernel"),
            ({"legacy": True}, "would override this package"),
            ({"legacy": "symlink"}, "would override this package"),
        ):
            with self.subTest(**kwargs):
                result = self.run_preinst(**kwargs)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_companions_reject_missing_or_unpatched_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "missing bundled Debian packages"):
                builder.companion_packages(root)
            (root / "kwin.deb").touch()
            with patch.object(builder, "output", side_effect=["kwin-common", "4:6.3.6-1", "amd64"]):
                with self.assertRaisesRegex(ValueError, "version marker"):
                    builder.companion_packages(root)

    def test_companions_reject_duplicate_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("first.deb", "second.deb"):
                (root / name).touch()
            with patch.object(builder, "output", side_effect=[
                "kwin-common", "4:6.3.6-1+weaselway1", "amd64",
                "kwin-common", "4:6.3.6-2+weaselway1", "amd64",
            ]):
                with self.assertRaisesRegex(ValueError, "multiple candidates"):
                    builder.companion_packages(root)


if __name__ == "__main__":
    unittest.main()
