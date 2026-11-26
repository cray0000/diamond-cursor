"""Manage the two optional GNOME scroll features for the current user."""
import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent
FEATURES = ("flick", "speed")
UNIT = "org.gnome.Shell@ubuntu.service"
LIB = "lib/libmutter-clutter-51.so.0"
FILES = ("prepare", "ubuntu.sha256", "recipe", LIB, "flick.conf", "speed.conf")
BUILD_INPUTS = ("mutter-51.patch", "build.sh", "prepare", "feature.conf.in")


def verify(release, manifest):
    return subprocess.run(["sha256sum", "--check", "--status", manifest], cwd=release).returncode == 0


def check_platform(feature):
    os_info = platform.freedesktop_os_release()
    if os_info.get("ID") != "ubuntu" or os_info.get("VERSION_ID") != "26.10":
        raise ValueError("This build supports Ubuntu 26.10 with GNOME on Wayland.")
    version = subprocess.check_output(
        ["dpkg-query", "-W", "-f=${Version} ${Architecture}", "libmutter-51-0"], text=True).strip()
    if version != "51.0-1ubuntu3 amd64":
        raise ValueError(f"This build needs Ubuntu Mutter 51.0-1ubuntu3 amd64. Found {version}.")
    subprocess.run(["systemctl", "--user", "cat", UNIT], stdout=subprocess.DEVNULL, check=True)
    if feature == "speed":
        subprocess.run(["gsettings", "range", "org.gnome.desktop.peripherals.touchpad", "scroll-speed"],
                       stdout=subprocess.DEVNULL, check=True)


def build_release(root, recipe):
    release = Path(tempfile.mkdtemp(prefix="build-", dir=root))
    try:
        subprocess.run([SOURCE / "build.sh", release], check=True)
        shutil.copy2(SOURCE / "prepare", release)
        template = (SOURCE / "feature.conf.in").read_text()
        for feature in FEATURES:
            (release / f"{feature}.conf").write_text(
                template.replace("@FLAG@", feature.upper()).replace("@NAME@", feature))
        (release / "recipe").write_text(recipe)
        with (release / "files.sha256").open("w") as output:
            subprocess.run(["sha256sum", *FILES], cwd=release, stdout=output, check=True)
        if not verify(release, "ubuntu.sha256"):
            raise ValueError("The Ubuntu libraries changed during the build. Run install again.")
    except BaseException:
        shutil.rmtree(release)
        raise
    return release


def remove_release(release):
    if not verify(release, "files.sha256"):
        print(f"Keeping edited build at {release}.", file=sys.stderr)
        return
    for name in (*FILES, "files.sha256"):
        (release / name).unlink()
    for directory in (release / "lib", release):
        if not any(directory.iterdir()):
            directory.rmdir()


def select_release(current, release, temp):
    if release is None:
        current.unlink(missing_ok=True)
    else:
        link = temp / "next"
        link.symlink_to(release.name)
        link.replace(current)


def manage(feature, action):
    if os.getuid() == 0:
        raise ValueError("Run this as your desktop user, without sudo.")
    parent = Path.home() / ".local/share/diamond-cursor"
    root = parent / "gnome-scroll"
    config = Path(os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config")
    units = config / "systemd/user" / f"{UNIT}.d"
    link = units / f"65-diamond-cursor-scroll-{feature}.conf"
    current = root / "current"
    target = current / f"{feature}.conf"
    if action == "uninstall" and not parent.exists():
        return
    parent.mkdir(parents=True, exist_ok=True)
    lock = os.open(parent, os.O_RDONLY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for name in FEATURES:
            conf = units / f"65-diamond-cursor-scroll-{name}.conf"
            if os.path.lexists(conf) and (not conf.is_symlink() or conf.readlink() != current / f"{name}.conf"):
                raise ValueError(f"Another configuration owns {conf}.")
        previous = None
        if os.path.lexists(current):
            if not current.is_symlink() or current.resolve().parent != root or not current.resolve().name.startswith("build-"):
                raise ValueError(f"Review the existing installation at {current}.")
            previous = current.resolve(strict=True)

        if action == "uninstall":
            if not link.is_symlink():
                return
            link.unlink()
            try:
                subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
            except BaseException:
                link.symlink_to(target)
                raise
            if not any((units / f"65-diamond-cursor-scroll-{name}.conf").is_symlink() for name in FEATURES):
                current.unlink(missing_ok=True)
                if previous:
                    remove_release(previous)
                if root.exists() and not any(root.iterdir()):
                    root.rmdir()
            return

        check_platform(feature)
        if (units / "60-diamond-cursor-scroll-lift.conf").exists():
            raise ValueError("Disable the earlier scroll-lift prototype before installing these extras.")
        recipe = hashlib.sha256(b"".join((SOURCE / name).read_bytes() for name in BUILD_INPUTS)).hexdigest()
        root.mkdir(exist_ok=True)
        units.mkdir(parents=True, exist_ok=True)
        if previous and not verify(previous, "files.sha256"):
            raise ValueError(f"Review the edited build at {previous}.")
        reuse = previous and (previous / "recipe").read_text() == recipe and verify(previous, "ubuntu.sha256")
        release = previous if reuse else build_release(root, recipe)
        was_enabled = link.is_symlink()
        with tempfile.TemporaryDirectory(dir=root) as temp:
            try:
                if release != previous:
                    select_release(current, release, Path(temp))
                if not was_enabled:
                    link.symlink_to(target)
                subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
            except BaseException:
                if not was_enabled:
                    link.unlink(missing_ok=True)
                if release != previous:
                    select_release(current, previous, Path(temp))
                    remove_release(release)
                raise
        if previous and previous != release:
            remove_release(previous)
    finally:
        os.close(lock)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("feature", choices=FEATURES)
    parser.add_argument("action", choices=("install", "uninstall"))
    args = parser.parse_args()
    os.umask(0o077)
    try:
        manage(args.feature, args.action)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
    print(f"Scroll {args.feature} {args.action} complete. Log out and back in to apply it.")
