# Debian WSL binary package

This bundle installs the complete Plasma runtime without compiling it on the
target machine. It contains `weaselway-wsl` and the patched KWin and FreeRDP
Debian packages that it requires, plus the required Wayland client backport.
Install **all** the bundled packages together.
Other dependencies are downloaded by apt.

## Compatibility

- Debian 13 (Trixie), amd64, in WSL2; not Debian 12, Ubuntu or ARM64.
- The exact Microsoft WSL kernel recorded in `BUILD-INFO`. Installation rejects
  any other kernel. A WSL kernel update requires a rebuilt package.
- systemd enabled in `/etc/wsl.conf`, WSLg enabled in Windows, and a Windows GPU
  driver with WSL support. The regular WSL user needs sudo access.
- Debian's Trixie, Trixie updates/security and Trixie backports apt sources.
- Only one Weaselway distro/viewer session can use the shared WSL GPU driver
  and default vsock port at a time.

Use a fresh distro, or one without another desktop/display manager running.
The package uses its patched Mesa globally, masks WSLg's audio user service,
and disables Linux suspend/hibernate so Windows manages power. It does not
include Flatpak GPU extensions or Bluetooth support.

## Install

Extract the bundle, enter its directory, and check its contents:

```sh
sha256sum -c SHA256SUMS
sudo apt update
sudo apt install --no-install-recommends ./*.deb
sudo ww-configure-user "$(id -un)"
```

Save your work, then run `wsl --shutdown` in Windows PowerShell. This stops
all WSL distros. Reopen Debian and run:

```sh
ww-start-session plasma
ww-start-viewer --select-monitors
```

Monitor positions are aligned on every connection. To skip the chooser,
use `ww-start-viewer /multimon` for all monitors or
`ww-start-viewer /multimon /monitors:1,2` for selected Windows monitor IDs.
`ww-start-viewer --list-monitors` lists the IDs.

Right Ctrl + Right Shift + M minimizes the viewer;
Right Ctrl + Right Shift + G releases or recaptures keyboard input.

## Existing source-script installations

The package installs commands in `/usr/bin`, not `/usr/local/bin`.
An old source-script installation has commands and systemd units under
`/usr/local/bin` and `/etc/systemd` that override package files. Do not mix the
two installation methods. Use a fresh Debian WSL instance for this bundle.
No live driver is reloaded and no desktop is stopped during package installation.

## Removal

Stop the desktop with `ww-start-session stop`, then:

```sh
sudo apt purge weaselway-wsl
```

Restart WSL to unload the driver and restore the stock Mesa runtime. The
patched KWin/FreeRDP dependency packages and desktop packages remain installed;
apt can replace those from the Debian repositories separately. User desktop
settings are not deleted.

## Building another bundle

On a Debian 13 build machine, first build and install the matching stack with
the source installer. Supply a native multi-output module archive as described
in the parent distro README; stock release modules are single-output.
Then build the daemon from the desired checkout and run:

```sh
make -C weaselwayd DXGDRM_INCLUDE="$HOME/.cache/weaselway-build"
python3 distro/build-deb.py --output "$HOME/Downloads/weaselway-debian13"
```

The builder needs `dpkg-dev`, `binutils`, `kmod` and Python 3, the built files
under `/opt/weaselway`, Mesa's source/license files, and the patched `.deb`
files in `~/.cache/weaselway-build/packages`. It downloads the pinned Windows
viewer's upstream copyright notices while building. It does not install anything or
modify the live system. Override the input directories with `--prefix`,
`--mesa-source` and `--packages`; `--output` must not exist yet.
Only one version of each companion package may be present.
The package directory must also contain `libwayland-client0` from Trixie
backports (`apt download libwayland-client0/trixie-backports`): apt does not
automatically select a backport to satisfy the newer Mesa's minimum version.

Source: <https://github.com/JakeHarrison11/weaselway> (revision in `BUILD-INFO`).
Mesa and Windows viewer revisions are pinned in `distro/install.py`; driver
source changes are in `nix/dxgdrm-multi-output.patch`. Companion Debian packages
retain their copyright metadata. Anyone redistributing the binary bundle must
also satisfy the source-distribution obligations of its included components.
