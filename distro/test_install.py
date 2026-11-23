import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from install import DebianTrixie, Desktop, InstallError, Options, Ubuntu, download_releases


class DxgdrmArchiveTests(unittest.TestCase):
    def test_local_module_archive_replaces_the_release_download(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            archive = work / "custom.tar.gz"
            archive.write_bytes(b"custom module archive")
            options = Options(Desktop.KDE, False, False, 8, False, dxgdrm_archive=archive)
            with patch("install.BUILD", work), patch("install.step"), patch("install.download") as download:
                download_releases(options)
            self.assertEqual((work / "dxgdrm.tar.gz").read_bytes(), archive.read_bytes())
            self.assertEqual([args[1].name for args, _ in download.call_args_list], ["dxgdrm_drm.h"])


class DebianPackagesTests(unittest.TestCase):
    def test_mesa_build_dependencies_use_backports(self) -> None:
        distro = DebianTrixie()
        options = Options(Desktop.KDE, False, False, 8, False)
        with (
            patch.object(distro, "enable_source_packages"),
            patch("install.write_root"),
            patch.object(distro, "apt_get") as apt,
        ):
            distro.install_packages(options)
        self.assertEqual(
            apt.call_args_list,
            [
                call("update"),
                call("install", "-y", *distro.packages(options)),
                call("build-dep", "-y", "-t", "trixie-backports", "mesa"),
            ],
        )

    def test_selects_rebuilt_winpr_utils_for_freerdp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            for name in ("freerdp3-dev", "libwinpr-tools3-3", "winpr3-utils", "winpr-utils", "freerdp3-x11"):
                (work / f"{name}.deb").touch()
            installed = {"freerdp3-dev": "old", "libwinpr-tools3-3": "old", "winpr3-utils": "old"}
            with patch("install.output", side_effect=lambda *args: Path(args[2]).stem):
                selected = Ubuntu.patched_debs("freerdp", installed, work)
            self.assertEqual(
                [path.name for path in selected],
                ["freerdp3-dev.deb", "libwinpr-tools3-3.deb", "winpr-utils.deb", "winpr3-utils.deb"],
            )

    def test_old_freerdp_build_without_winpr_utils(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            (work / "freerdp3-dev.deb").touch()
            with patch("install.output", side_effect=lambda *args: Path(args[2]).stem):
                selected = Ubuntu.patched_debs("freerdp", {"freerdp3-dev": "old"}, work)
            self.assertEqual([path.name for path in selected], ["freerdp3-dev.deb"])


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
