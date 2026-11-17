import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from install import DebianTrixie, InstallError


class DebianSourcesTests(unittest.TestCase):
    def test_numbered_source_file(self) -> None:
        content = (
            "Types: deb\n"
            "URIs: https://deb.debian.org/debian\n"
            "Suites: trixie trixie-updates trixie-backports\n"
            "Components: main\n"
            "Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp\n\n"
            "Types: deb\n"
            "URIs: https://security.debian.org/debian-security\n"
            "Suites: trixie-security\n"
            "Components: main\n"
            "Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            sources = directory / "0000debian.sources"
            sources.write_text(content)
            with patch("install.write_root") as write:
                DebianTrixie().enable_source_packages(directory)
            write.assert_called_once_with(sources, content.replace("Types: deb\n", "Types: deb deb-src\n"))

    def test_multiple_files_and_already_enabled_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "debian.sources").write_text("Types: deb deb-src\nURIs: https://deb.debian.org/debian\n")
            security = directory / "security.sources"
            security.write_text("Types:\tdeb \t\nURIs: https://security.debian.org/debian-security\n")
            with patch("install.write_root") as write:
                DebianTrixie().enable_source_packages(directory)
            write.assert_called_once_with(
                security, "Types:\tdeb deb-src\nURIs: https://security.debian.org/debian-security\n"
            )

    def test_already_enabled_sources_are_not_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "0000debian.sources").write_text("Types: deb deb-src\n")
            with patch("install.write_root") as write:
                DebianTrixie().enable_source_packages(directory)
            write.assert_not_called()

    def test_missing_source_entries_fail_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(InstallError, "no deb or deb-src entries"):
                DebianTrixie().enable_source_packages(Path(temporary))


if __name__ == "__main__":
    unittest.main()
