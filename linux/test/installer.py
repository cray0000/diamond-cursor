"""Exercise the Ubuntu scripts in a disposable bubblewrap filesystem."""

from pathlib import Path
import subprocess
import tempfile
import unittest


LINUX = Path(__file__).resolve().parents[1]
CONFIG = (LINUX / "diamond.conf").read_bytes()
QUIRK = (LINUX / "keyd.quirks").read_bytes()


class InstallerTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.etc = self.root / "etc"
        self.etc.mkdir()
        (self.etc / "os-release").write_text("ID=ubuntu\n")
        self.target = self.etc / "keyd/diamond.conf"
        self.quirks = self.etc / "libinput/local-overrides.quirks"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "commands"
        self.log.touch()
        self.stub("dpkg-query", '[ ! -e /tmp/state/package ] || echo installed')
        self.stub("apt-get", '''
            echo "apt-get $*" >> /tmp/state/commands
            if [ "$1" = install ]; then
                [ ! -e /tmp/state/apt-error ] || exit 100
                touch /tmp/state/package
            fi
        ''')
        self.stub("systemctl", '''
            echo "systemctl $*" >> /tmp/state/commands
            case "$1" in
                cat) test -f /tmp/state/upstream-unit ;;
                restart) touch /tmp/state/active ;;
                is-active) test -f /tmp/state/active ;;
            esac
        ''')

    def stub(self, name, body):
        script = self.bin / name
        script.write_text("#!/bin/sh\nset -eu\n" + body + "\n")
        script.chmod(0o755)

    def run_script(self, name, success=True, uid=0):
        result = subprocess.run([
            "bwrap", "--unshare-all", "--die-with-parent", "--uid", str(uid), "--gid", str(uid),
            "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/run",
            "--dir", "/run/systemd/system", "--tmpfs", "/tmp", "--bind", self.root, "/tmp/state",
            "--bind", self.etc, "/etc", "--ro-bind", LINUX, "/tmp/config repo/linux",
            "--setenv", "PATH", "/tmp/state/bin:/usr/bin:/bin", "--chdir", "/tmp/config repo",
            "--", f"./linux/{name}.sh",
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_install_reinstall_remove(self):
        self.run_script("install")
        self.assertEqual(self.target.read_bytes(), CONFIG)
        self.assertEqual(self.quirks.read_bytes(), QUIRK)
        actions = self.log.read_text().splitlines()
        self.assertIn("apt-get install -y keyd", actions)
        self.assertIn("systemctl enable keyd.service", actions)
        self.assertIn("systemctl restart keyd.service", actions)
        device = self.target.with_name("external.conf")
        device.write_text("[ids]\n1234:5678\n")
        self.log.write_text("")
        self.run_script("install")
        self.assertEqual(self.quirks.read_bytes(), QUIRK)
        self.assertNotIn("apt-get", self.log.read_text())
        self.run_script("uninstall")
        self.assertFalse(self.target.exists())
        self.assertFalse(self.quirks.exists())
        self.assertIn("systemctl try-restart keyd.service", self.log.read_text())
        self.run_script("uninstall")
        self.assertTrue(device.exists())
        self.assertTrue((self.root / "package").exists())

    def test_existing_libinput_overrides(self):
        self.quirks.parent.mkdir()
        for existing in (b"[My keyboard]\nMatchName=My keyboard\nAttrKeyboardIntegration=external\n",
                         b"[keyd virtual keyboard]\nMatchUdevType=keyboard\n"
                         b"MatchName=keyd virtual keyboard\nAttrKeyboardIntegration=internal\n"):
            with self.subTest(existing=existing):
                self.quirks.write_bytes(existing)
                result = self.run_script("install")
                self.assertIn("Touchpad pairing", result.stdout)
                self.assertEqual(self.target.read_bytes(), CONFIG)
                self.assertEqual(self.quirks.read_bytes(), existing)
                self.run_script("uninstall")
                self.assertEqual(self.quirks.read_bytes(), existing)

    def test_edited_libinput_overrides(self):
        self.run_script("install")
        edited = QUIRK + b"\n[My keyboard]\nMatchName=My keyboard\nAttrKeyboardIntegration=external\n"
        self.quirks.write_bytes(edited)
        self.run_script("install")
        self.run_script("uninstall")
        self.assertEqual(self.quirks.read_bytes(), edited)

    def test_linked_libinput_overrides(self):
        self.quirks.parent.mkdir()
        other = self.quirks.with_name("my-quirks")
        self.quirks.symlink_to(other.name)
        for exists in (False, True):
            with self.subTest(exists=exists):
                if exists:
                    other.write_bytes(QUIRK)
                self.run_script("install")
                self.run_script("uninstall")
                self.assertTrue(self.quirks.is_symlink())
                self.assertEqual(other.exists(), exists)
                if exists:
                    self.assertEqual(other.read_bytes(), QUIRK)

    def test_remove_rule_after_mapping_was_manually_removed(self):
        self.run_script("install")
        self.target.unlink()
        self.run_script("uninstall")
        self.assertFalse(self.quirks.exists())

    def test_custom_configs(self):
        self.target.parent.mkdir()
        self.target.write_text("my custom config")
        for script in ("install", "uninstall"):
            self.run_script(script, success=False)
            self.assertEqual(self.target.read_text(), "my custom config")
        self.target.unlink()
        self.target.with_name("default.conf").write_text("[ids]\n  *  \n")
        self.run_script("install", success=False)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.quirks.exists())

    def test_link_to_another_config(self):
        self.target.parent.mkdir()
        other = self.target.with_name("my-keyboard.conf")
        other.write_bytes(CONFIG)
        self.target.symlink_to(other.name)
        for script in ("install", "uninstall"):
            self.run_script(script, success=False)
            self.assertTrue(self.target.is_symlink())
            self.assertEqual(other.read_bytes(), CONFIG)

    def test_unavailable_package(self):
        (self.root / "apt-error").touch()
        result = self.run_script("install", success=False)
        self.assertIn("upstream instructions", result.stderr)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.quirks.exists())
        self.assertNotIn("systemctl restart", self.log.read_text())

    def test_upstream_install(self):
        (self.root / "upstream-unit").touch()
        self.run_script("install")
        self.assertEqual(self.target.read_bytes(), CONFIG)
        self.assertNotIn("apt-get", self.log.read_text())

    def test_other_distribution(self):
        (self.etc / "os-release").write_text("ID=linuxmint\nID_LIKE=ubuntu\n")
        for script in ("install", "uninstall"):
            result = self.run_script(script, success=False, uid=1000)
            self.assertIn("package manager", result.stderr)
        self.assertEqual(self.log.read_text(), "")
        self.assertFalse(self.target.exists())

    def test_elevation_from_repo_root(self):
        self.stub("sudo", 'printf "%s\\n" "$PWD $*" >> /tmp/state/commands')
        for script in ("install", "uninstall"):
            self.run_script(script, uid=1000)
            self.assertIn(f"/tmp/config repo/linux -- ./{script}.sh", self.log.read_text())


if __name__ == "__main__":
    unittest.main()
