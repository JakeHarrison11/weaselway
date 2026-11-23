#!/usr/bin/env python3
"""Package a built Debian 13 Plasma stack; never installs or changes the host."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

REPO = Path(__file__).resolve().parent.parent
COMPANIONS = (
    "kwin-wayland", "kwin-common", "kwin-data", "libkwin6",
    "libfreerdp3-3", "libfreerdp-server3-3", "libwinpr3-3", "libwayland-client0",
)
VIEWER_NOTICES = {
    "FreeRDP": ("weaselway/freerdp/v1.3.0", "LICENSE"),
    "SDL3": ("libsdl-org/SDL/release-3.4.14", "LICENSE.txt"),
    "SDL3_ttf": ("libsdl-org/SDL_ttf/release-3.2.2", "LICENSE.txt"),
    "OpenSSL": ("openssl/openssl/openssl-3.6.3", "LICENSE.txt"),
    "FreeType": ("libsdl-org/freetype/9973564cfa63763a3e4ac67c09147899539b1e07", "docs/FTL.TXT"),
    "HarfBuzz": ("libsdl-org/harfbuzz/564bf9818a18709776856533829c0c04950773d6", "COPYING"),
    "PlutoSVG": ("libsdl-org/plutosvg/2983eb6919feea272d793bc386384e3f5b97b03c", "LICENSE"),
    "PlutoVG": ("libsdl-org/plutovg/3e6f922f453da1c9e7d1d7f66cac1d9724a18b47", "LICENSE"),
}


def output(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def write(root, path, text, mode=0o644):
    destination = root / path.lstrip("/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text)
    destination.chmod(mode)


def copy(root, source, destination, mode=None):
    target = root / destination.lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if mode is not None:
        target.chmod(mode)


def companion_packages(directory):
    result = {}
    for path in sorted(directory.rglob("*.deb")):
        name = output("dpkg-deb", "-f", str(path), "Package")
        if name in COMPANIONS:
            version = output("dpkg-deb", "-f", str(path), "Version")
            architecture = output("dpkg-deb", "-f", str(path), "Architecture")
            marker = "~bpo13" if name == "libwayland-client0" else "weaselway"
            if marker not in version or architecture not in ("all", "amd64"):
                raise ValueError(f"{path}: expected amd64/all with version marker {marker!r}")
            if name in result:
                raise ValueError(f"multiple candidates for {name}; use a directory with one version")
            result[name] = (path, version)
    missing = set(COMPANIONS) - result.keys()
    if missing:
        raise ValueError("missing bundled Debian packages: " + ", ".join(sorted(missing)))
    return result


def check_module(module, kernel):
    if output("modinfo", "-F", "vermagic", str(module)).split()[0] != kernel:
        raise ValueError("dxgdrm.ko does not match the running WSL kernel")
    # The released multi-output driver logs this message during probe.
    if b"render node and virtual display (%u outputs, first %ux%u)" not in module.read_bytes():
        raise ValueError("dxgdrm.ko lacks native multi-output support")


def stage_runtime(root, prefix, kernel):
    for name in ("mesa", "viewer"):
        shutil.copytree(prefix / name, root / "opt/weaselway" / name, symlinks=True)
    # Development files are not part of the installed runtime.
    for directory in ("include", "lib/pkgconfig"):
        shutil.rmtree(root / "opt/weaselway/mesa" / directory)
    for path in (root / "opt/weaselway/mesa/lib").glob("*.a"):
        path.unlink()
    modules = prefix / "dxgdrm/lib/modules" / kernel / "extra"
    for module in modules.glob("*.ko"):
        copy(root, module, f"/opt/weaselway/dxgdrm/lib/modules/{kernel}/extra/{module.name}")
    for name in ("modules.order", "modules.builtin", "modules.builtin.modinfo"):
        # WSL's module tree supplies the exact kernel's built-in module metadata.
        source = Path("/lib/modules") / kernel / name
        copy(root, source, f"/opt/weaselway/dxgdrm/lib/modules/{kernel}/{name}")
    copy(root, prefix / "dxgdrm/lib/udev/rules.d/99-dxgdrm.rules",
         "/usr/lib/udev/rules.d/99-dxgdrm.rules")
    subprocess.run(["depmod", "-b", str(root / "opt/weaselway/dxgdrm"), kernel], check=True)
    copy(root, REPO / "weaselwayd/weaselwayd", "/usr/bin/weaselwayd", 0o755)
    for name in ("ww-start-session", "ww-start-viewer", "ww-install-viewer-link"):
        copy(root, REPO / "bin" / f"{name}.sh", f"/usr/bin/{name}", 0o755)
    copy(root, REPO / "distro/debian/ww-configure-user", "/usr/sbin/ww-configure-user", 0o755)
    copy(root, REPO / "libexec/prep-session.sh", "/opt/weaselway/libexec/prep-session.sh", 0o755)
    copy(root, REPO / "environment.d/10-weaselway.conf", "/etc/environment.d/10-weaselway.conf")
    copy(root, REPO / "pipewire/pipewire.conf.d/10-weaselway-rdp-audio.conf",
         "/etc/pipewire/pipewire.conf.d/10-weaselway-rdp-audio.conf")
    write(root, "/etc/ld.so.conf.d/00-weaselway-mesa.conf", "/opt/weaselway/mesa/lib\n")
    write(root, "/etc/environment.d/11-weaselway-distro.conf",
          "LIBVA_DRIVERS_PATH=/opt/weaselway/mesa/lib/dri\nWEASELWAY_DEFAULT_SESSION=plasma\n")
    write(root, "/etc/profile.d/weaselway.sh",
          'unset PULSE_SERVER\n'
          'export WEASELWAY_VIEWER="${WEASELWAY_VIEWER:-/opt/weaselway/viewer/sdl-freerdp.exe}"\n'
          'export WEASELWAY_DEFAULT_SESSION="${WEASELWAY_DEFAULT_SESSION:-plasma}"\n')
    write(root, "/usr/lib/udev/rules.d/70-weaselway-uinput.rules",
          'KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input", MODE="0660"\n')
    write(root, "/usr/lib/systemd/system/weaselway-prep.service",
          "[Unit]\nDescription=Weaselway host preparation\n"
          "After=local-fs.target wslg.service systemd-udevd.service\n\n"
          "[Service]\nType=oneshot\nRemainAfterExit=yes\n"
          "Environment=DXGDRM_ROOT=/opt/weaselway/dxgdrm\n"
          "ExecStart=/opt/weaselway/libexec/prep-session.sh\n\n"
          "[Install]\nWantedBy=multi-user.target\n")
    write(root, "/usr/lib/systemd/user/weaselwayd.service",
          "[Unit]\nDescription=Weaselway display server\nConditionUser=!root\n"
          "ConditionPathExists=/etc/systemd/user/weaselwayd.service.d/10-weaselway-user.conf\n\n"
          "[Service]\nExecStart=/usr/bin/weaselwayd\nRestart=on-failure\nRestartSec=2\n\n"
          "[Install]\nWantedBy=default.target\n")
    write(root, "/etc/systemd/system/user@.service.d/weaselway.conf", "[Service]\nLimitNICE=-11\n")
    write(root, "/etc/systemd/system/modprobe@drm.service.d/weaselway.conf",
          "[Service]\nExecStart=\nExecStart=-modprobe -abq -d /opt/weaselway/dxgdrm drm\n")
    write(root, "/etc/systemd/sleep.conf.d/weaselway.conf",
          "[Sleep]\nAllowSuspend=no\nAllowHibernation=no\nAllowHybridSleep=no\n"
          "AllowSuspendThenHibernate=no\n")
    write(root, "/etc/UPower/UPower.conf.d/weaselway.conf",
          "[UPower]\nCriticalPowerAction=Ignore\nAllowRiskyCriticalPowerAction=true\n")
    for path, target in (
        ("/etc/systemd/user/wslg-session.service", "/dev/null"),
        ("/etc/vulkan/icd.d/dzn_icd.x86_64.json",
         "/opt/weaselway/mesa/share/vulkan/icd.d/dzn_icd.x86_64.json"),
    ):
        dest = root / path.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(target)


def dependencies(work, root, companions):
    write(work, "/debian/control",
          "Source: weaselway-wsl\n\nPackage: weaselway-wsl\nArchitecture: amd64\n"
          "Description: Weaselway WSL runtime\n")
    binaries = [root / "usr/bin/weaselwayd"]
    for path in (root / "opt/weaselway/mesa").rglob("*"):
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as file:
                if file.read(4) == b"\x7fELF":
                    binaries.append(path)
    subprocess.run(["strip", "--strip-unneeded", *map(str, binaries)], check=True)
    calculated = output(
        "dpkg-shlibdeps", "-O", "-xweaselway-wsl",
        "-l" + str((root / "opt/weaselway/mesa/lib").relative_to(work)),
        *("-e" + str(path.relative_to(work)) for path in binaries), cwd=work,
    )
    if not calculated.startswith("shlibs:Depends="):
        raise ValueError("dpkg-shlibdeps did not produce runtime dependencies")
    required = calculated.removeprefix("shlibs:Depends=").split(", ")
    required += [f"{name} (= {version})" for name, (_, version) in companions.items()]
    required += [
        "sudo", "systemd-sysv", "dbus-user-session", "udev", "kmod",
        "init-system-helpers (>= 1.52)", "passwd", "libpam-systemd", "kbd",
        "plasma-desktop", "plasma-workspace", "libkscreen-bin", "konsole", "dolphin",
        "xdg-desktop-portal-kde", "pipewire-pulse", "wireplumber", "upower",
        "libegl1", "libgles2", "libglx0", "libgl1", "libedit2",
    ]
    return ", ".join(sorted(set(required)))


def build(args):
    os.umask(0o022)
    if output("dpkg", "--print-architecture") != "amd64":
        raise ValueError("build this package on Debian 13 amd64")
    release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines()
                   if "=" in line)
    if release.get("ID", "").strip('"') != "debian" or release.get("VERSION_ID", "").strip('"') != "13":
        raise ValueError("build this package on Debian 13 amd64")
    kernel = os.uname().release
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH") or output(
        "git", "-C", str(REPO), "log", "-1", "--format=%ct"
    ))
    build_info = (
        f"kernel={kernel}\narchitecture=amd64\ndistribution=debian-13\n"
        f"weaselway_commit={output('git', '-C', str(REPO), 'rev-parse', 'HEAD')}\n"
        "mesa_source=https://github.com/weaselway/mesa/tree/8aa6a89c3da6bc894f8baff96320be5150169fcf\n"
        "viewer_source=https://github.com/weaselway/freerdp/tree/v1.3.0\n"
        "dxgdrm_source=https://github.com/weaselway/dxgdrm/tree/v1.4.0\n"
        f"kernel_source=https://github.com/microsoft/WSL2-Linux-Kernel/tree/linux-msft-wsl-{kernel.split('-')[0]}\n"
    )
    module = args.prefix / "dxgdrm/lib/modules" / kernel / "extra/dxgdrm.ko"
    check_module(module, kernel)
    companions = companion_packages(args.packages)
    destination = args.output.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="weaselway-deb-") as directory:
        work = Path(directory)
        root = work / "debian/weaselway-wsl"
        stage_runtime(root, args.prefix, kernel)
        (root / "DEBIAN").mkdir()
        depends = dependencies(work, root, companions)
        write(root, "/DEBIAN/control",
              f"Package: weaselway-wsl\nVersion: {args.version}\nArchitecture: amd64\n"
              "Section: misc\nPriority: optional\n"
              "Maintainer: Weaselway contributors <noreply@github.com>\n"
              f"Depends: {depends}\n"
              f"Installed-Size: {sum(p.lstat().st_size for p in root.rglob('*')) // 1024}\n"
              "Homepage: https://github.com/JakeHarrison11/weaselway\n"
              f"Description: GPU-accelerated Plasma desktop for Debian WSL\n"
              f" Includes multi-monitor dxgdrm for WSL kernel {kernel},\n"
              " patched Mesa, the Windows viewer, and session integration.\n")
        for name in ("preinst", "postinst", "postrm"):
            text = (REPO / "distro/debian" / name).read_text().replace("@KERNEL@", kernel)
            write(root, "/DEBIAN/" + name, text, 0o755)
        write(root, "/DEBIAN/triggers", "activate-noawait ldconfig\n")
        conffiles = sorted("/" + str(p.relative_to(root)) for p in (root / "etc").rglob("*")
                           if p.is_file() and not p.is_symlink())
        write(root, "/DEBIAN/conffiles", "\n".join(conffiles) + "\n")
        doc = "/usr/share/doc/weaselway-wsl"
        write(root, doc + "/BUILD-INFO", build_info)
        copy(root, REPO / "LICENSE", doc + "/weaselway-LICENSE")
        write(root, doc + "/copyright",
              "Weaselway: Copyright (c) 2026 Weaselway contributors, MIT; see weaselway-LICENSE.\n"
              "Mesa: multiple authors/licenses; see mesa-license.rst and mesa-licenses/.\n"
              "dxgdrm and drm_kms_helper: GPL-2.0; see /usr/share/common-licenses/GPL-2.\n"
              "Windows viewer: FreeRDP and OpenSSL, Apache-2.0; SDL3/SDL3_ttf, zlib;\n"
              "FreeType, FTL; HarfBuzz, MIT; PlutoSVG/PlutoVG, MIT.\n"
              "Portions of the viewer use the FreeType Project (https://freetype.org/).\n"
              "Full upstream notices are in viewer-licenses/. Sources and build instructions\n"
              "are identified in README.md, BUILD-INFO and the upstream repositories.\n")
        for name, (revision, path) in VIEWER_NOTICES.items():
            url = f"https://raw.githubusercontent.com/{revision}/{path}"
            notice = root / doc.lstrip("/") / "viewer-licenses" / (name + "-LICENSE")
            notice.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=30) as source, notice.open("wb") as target:
                shutil.copyfileobj(source, target)
        copy(root, REPO / "distro/debian/README.md", "/usr/share/doc/weaselway-wsl/README.md")
        copy(root, args.mesa_source / "docs/license.rst", "/usr/share/doc/weaselway-wsl/mesa-license.rst")
        shutil.copytree(args.mesa_source / "licenses", root / "usr/share/doc/weaselway-wsl/mesa-licenses")
        date = datetime.fromtimestamp(epoch, timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        changelog = (
            f"weaselway-wsl ({args.version}) trixie; urgency=medium\n\n"
            "  * Package the native multi-monitor Plasma desktop and matching WSL driver.\n\n"
            f" -- Weaselway contributors <noreply@github.com>  {date}\n"
        )
        (root / doc.lstrip("/") / "changelog.gz").write_bytes(
            gzip.compress(changelog.encode(), mtime=epoch)
        )
        write(root, "/usr/share/lintian/overrides/weaselway-wsl",
              "# Patched Mesa embeds /opt/weaselway paths and must override stock Mesa.\n"
              "weaselway-wsl: dir-or-file-in-opt [opt/weaselway/]\n"
              "weaselway-wsl: dir-or-file-in-opt [opt/weaselway/*]\n"
              "weaselway-wsl: package-modifies-ld.so-search-path [etc/ld.so.conf.d/00-weaselway-mesa.conf]\n"
              "# Private libraries are outside libc-bin's standard library search paths.\n"
              "weaselway-wsl: package-has-unnecessary-activation-of-ldconfig-trigger\n")
        for path in root.rglob("*"):
            if path.is_symlink():
                continue
            if path.is_dir():
                path.chmod(0o755)
            else:
                executable = path.stat().st_mode & 0o111 and ".so" not in path.name
                path.chmod(0o755 if executable else 0o644)
            os.utime(path, (epoch, epoch))
        package = destination / f"weaselway-wsl_{args.version}_amd64.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(root), str(package)],
                       check=True)
    for path, _ in companions.values():
        shutil.copy2(path, destination / path.name)
    shutil.copy2(REPO / "distro/debian/README.md", destination / "README.md")
    write(destination, "/BUILD-INFO", build_info)
    checksums = []
    for path in sorted(destination.glob("*.deb")):
        with path.open("rb") as file:
            checksums.append(f"{hashlib.file_digest(file, 'sha256').hexdigest()}  {path.name}")
    write(destination, "/SHA256SUMS", "\n".join(checksums) + "\n")
    archive = destination.parent / (destination.name + ".tar.gz")
    with tarfile.open(archive, "x:gz") as tar:
        tar.add(destination, arcname=destination.name)
    print(f"\nBuilt {archive}\nInstall all bundled .deb files together; see {destination / 'README.md'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    cache = Path.home() / ".cache/weaselway-build"
    parser.add_argument("--prefix", type=Path, default=Path("/opt/weaselway"))
    parser.add_argument("--packages", type=Path, default=cache / "packages")
    parser.add_argument("--mesa-source", type=Path, default=cache / "mesa")
    parser.add_argument("--output", type=Path, required=True, help="new directory for the install bundle")
    parser.add_argument("--version", default="0.1.0+multimon1")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9][A-Za-z0-9.+~]*", args.version):
        parser.error("version must be a Debian upstream version without an epoch or revision")
    try:
        build(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
