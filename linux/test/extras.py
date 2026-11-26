"""Check optional desktop settings and hardware selection in a disposable filesystem."""

import unittest

from installer import InstallerSandbox


class TypingDelayTest(InstallerSandbox):
    def setUp(self):
        super().setUp()
        self.setting = self.root / "setting"
        self.stub("dconf", 'if test -f /tmp/state/setting; then cat /tmp/state/setting; fi')
        self.stub("gsettings", '''
            test "$2 $3" = "org.gnome.desktop.peripherals.touchpad disable-while-typing-timeout"
            case "$1" in
                writable) test -f /tmp/state/locked && echo false || echo true ;;
                get) cat /tmp/state/setting 2>/dev/null || echo 'uint32 500' ;;
                set) printf 'uint32 %s\n' "${4#uint32 }" > /tmp/state/setting ;;
                reset) rm /tmp/state/setting ;;
            esac
        ''')

    def delay(self, action, **kwargs):
        return self.run_script("extras/typing-delay", action, uid=1000, **kwargs)

    def test_restore_default_or_custom_value_after_reinstall(self):
        for before in (None, "uint32 750\n", "uint32 300\n"):
            with self.subTest(before=before):
                if before is not None:
                    self.setting.write_text(before)
                self.delay("install")
                self.delay("install")
                self.assertEqual(self.setting.read_text(), "uint32 300\n")
                self.delay("uninstall")
                self.delay("uninstall")
                self.assertEqual(self.setting.read_text() if self.setting.exists() else None, before)

    def test_keep_subsequent_user_change(self):
        self.delay("install")
        self.setting.write_text("uint32 400\n")
        self.delay("uninstall")
        self.assertEqual(self.setting.read_text(), "uint32 400\n")

    def test_unavailable_setting_and_root(self):
        (self.root / "locked").touch()
        self.assertIn("writable", self.delay("install", success=False).stderr)
        self.assertIn("without sudo", self.run_script("extras/typing-delay", "install", success=False).stderr)
        self.assertFalse(self.setting.exists())


class PalmFilterTest(InstallerSandbox):
    unit = "diamond-cursor-palm-filter.service"
    rule = "99-diamond-cursor-palm-filter.rules"

    def setUp(self):
        super().setUp()
        self.mounts.extend(["--ro-bind", "/etc/alternatives", "/etc/alternatives"])
        for directory, mount in (("lib", "/usr/local/lib"), ("input", "/dev/input"), ("sys", "/sys")):
            path = self.root / directory
            path.mkdir()
            self.mounts.extend(["--bind", path, mount])
        self.bundle = self.root / "lib/diamond-cursor-palm-filter"
        self.unit_link = self.etc / "systemd/system" / self.unit
        self.unit_link.parent.mkdir(parents=True)
        self.rule_link = self.etc / "udev/rules.d" / self.rule
        self.input = self.root / "input"
        (self.input / "by-path").mkdir()
        self.properties = self.pad("event5", "125")
        self.stub("unpalm", 'echo "usage: --margin-left --margin-right --block-taps"')
        self.stub("udevadm", '''
            case "$1/${3:-}" in
                info/property) cat "/tmp/state/$(basename "$5").props" ;;
                info/symlink) echo "input/by-path/platform-$(basename "$5")-event-mouse" ;;
                trigger/--settle)
                    if test -L /etc/udev/rules.d/99-diamond-cursor-palm-filter.rules; then
                        ln -sf "$4" /dev/input/diamondpalm
                    else
                        rm -f /dev/input/diamondpalm
                    fi ;;
            esac
        ''')
        self.stub("systemctl", '''
            echo "$*" >> /tmp/state/commands
            case "$1" in
                is-active) test "$3" = diamond-cursor-palm-filter.service && test -f /tmp/state/active ;;
                is-enabled) test "$3" = diamond-cursor-palm-filter.service && test -f /tmp/state/enabled ;;
                enable) touch /tmp/state/enabled ;;
                start)
                    test ! -f /tmp/state/fail-start
                    mkdir -p /sys/devices/virtual/input/input99
                    echo 'Filtered Touchpad' > /sys/devices/virtual/input/input99/name
                    touch /tmp/state/active ;;
                disable) rm -f /tmp/state/active /tmp/state/enabled /sys/devices/virtual/input/input99/name ;;
            esac
        ''')

    def pad(self, node, width):
        (self.input / node).touch()
        (self.input / "by-path" / f"platform-{node}-event-mouse").symlink_to("../" + node)
        props = self.root / (node + ".props")
        props.write_text(f"DEVPATH=/devices/platform/{node}\nID_INPUT_TOUCHPAD=1\nID_BUS=i2c\nID_INPUT_WIDTH_MM={width}\n")
        return props

    def palm(self, action, *args, **kwargs):
        return self.run_script("extras/palm-filter", action, *args, **kwargs)

    def test_devices_margins_startup_and_removal(self):
        self.pad("event8", "100").write_text("ID_INPUT_TOUCHPAD=1\nDEVPATH=/devices/virtual/input/input8/event8\n")
        for width, percent in (("125", "24"), ("100", "30"), ("115", "26.086957")):
            with self.subTest(width=width):
                self.properties.write_text(f"ID_INPUT_TOUCHPAD=1\nID_BUS=i2c\nID_INPUT_WIDTH_MM={width}\n")
                self.palm("install")
                self.palm("install")
                unit = (self.bundle / self.unit).read_text()
                rounded = f"{float(percent):.6f}"
                self.assertIn(f"--margin-left {rounded} --margin-right {rounded} --block-taps", unit)
                self.assertIn("WantedBy=dev-input-diamondpalm.device", unit)
                rule = (self.bundle / self.rule).read_text()
                self.assertIn('SYMLINK=="input/by-path/platform-event5-event-mouse"', rule)
                self.assertIn('ENV{ID_INPUT_TOUCHPAD_INTEGRATION}="internal"', rule)
                self.assertTrue((self.root / "active").exists())
                self.palm("uninstall")
                self.palm("uninstall")
                self.assertFalse(self.bundle.exists())
                self.assertFalse(self.rule_link.is_symlink())
                self.assertFalse(self.unit_link.is_symlink())
                self.assertFalse((self.root / "enabled").exists())
                self.assertTrue((self.bin / "unpalm").exists())

    def test_select_one_of_multiple_pads(self):
        self.pad("event6", "100")
        self.palm("install", success=False)
        self.palm("install", "/dev/input/event6")
        self.assertIn("event6", (self.bundle / "device").read_text())

    def test_unsupported_or_ambiguous_geometry(self):
        for width in ("", "60", "bogus"):
            self.properties.write_text(f"ID_INPUT_TOUCHPAD=1\nID_BUS=i2c\nID_INPUT_WIDTH_MM={width}\n")
            self.assertIn("width", self.palm("install", success=False).stderr)
        self.assertFalse(self.bundle.exists())

    def test_explicit_selection_rejects_external_touchpads_and_touchscreens(self):
        for flag in ("ID_INPUT_TOUCHPAD_INTEGRATION=external", "ID_INPUT_TOUCHSCREEN=1"):
            self.properties.write_text(f"ID_INPUT_TOUCHPAD=1\nID_INPUT_WIDTH_MM=125\n{flag}\n")
            self.palm("install", "/dev/input/event5", success=False)
        self.assertFalse(self.bundle.exists())

    def test_edited_service_is_preserved(self):
        self.palm("install")
        unit = self.bundle / self.unit
        unit.write_text(unit.read_text() + "\n# Local edit\n")
        self.palm("uninstall", success=False)
        self.assertIn("# Local edit", unit.read_text())
        self.assertTrue(self.unit_link.is_symlink())

    def test_preserve_other_installations(self):
        name = self.root / "sys/devices/virtual/input/input9/name"
        name.parent.mkdir(parents=True)
        name.write_text("Filtered Touchpad\n")
        self.assertIn("separate unpalm", self.palm("install", success=False).stderr)
        name.unlink()
        self.unit_link.write_text("hand-written service")
        self.palm("install", success=False)
        self.palm("uninstall", success=False)
        self.assertEqual(self.unit_link.read_text(), "hand-written service")

    def test_failed_start_rolls_back_and_can_retry(self):
        failure = self.root / "fail-start"
        failure.touch()
        self.palm("install", success=False)
        self.assertFalse(self.bundle.exists())
        self.assertFalse(self.rule_link.is_symlink())
        self.assertFalse(self.unit_link.is_symlink())
        self.assertFalse((self.input / "diamondpalm").is_symlink())
        failure.unlink()
        self.palm("install")

    def test_reject_bad_download(self):
        (self.bin / "unpalm").unlink()
        self.stub("uname", 'echo x86_64')
        self.stub("curl", 'until [ "$1" = -o ]; do shift; done; echo invalid > "$2"')
        self.assertIn("checksum", self.palm("install", success=False).stderr)
        self.assertFalse(self.bundle.exists())


class ScrollExtrasTest(InstallerSandbox):
    def setUp(self):
        super().setUp()
        self.home = self.root / "home"
        self.home.mkdir()
        self.bundle = self.home / ".local/share/diamond-cursor/gnome-scroll"
        self.units = self.home / ".config/systemd/user/org.gnome.Shell@ubuntu.service.d"
        (self.etc / "os-release").write_text("ID=ubuntu\nVERSION_ID=26.10\n")
        self.stub("dpkg-query", "echo '51.0-1ubuntu3 amd64'")
        self.stub("gsettings", 'test "$1" = range')
        self.stub("systemctl", 'test ! -f /tmp/state/reload-error || test "$2" != daemon-reload')
        self.stub("build", '''
            echo build >> /tmp/state/commands
            test ! -f /tmp/state/build-error
            mkdir "$1/lib"
            echo library > "$1/lib/libmutter-clutter-51.so.0"
            sha256sum /etc/os-release > "$1/ubuntu.sha256"
        ''')
        self.mounts += [
            "--setenv", "HOME", "/tmp/state/home",
            "--setenv", "XDG_CONFIG_HOME", "/tmp/state/home/.config",
            "--ro-bind", self.bin / "build", "/tmp/config repo/linux/extras/gnome-scroll/build.sh",
        ]

    def extra(self, name, action, **kwargs):
        return self.run_script(f"extras/scroll-{name}", action, uid=1000, **kwargs)

    def prepare(self):
        return self.run_sandbox(["/tmp/state/home/.local/share/diamond-cursor/gnome-scroll/current/prepare",
                                 "/tmp/state/login.env"], uid=1000)

    def conf(self, name):
        return self.units / f"65-diamond-cursor-scroll-{name}.conf"

    def test_independent_install_and_removal_in_both_orders(self):
        for first, second in (("flick", "speed"), ("speed", "flick")):
            with self.subTest(first=first):
                self.log.write_text("")
                self.extra(first, "install")
                self.extra(first, "install")
                self.assertTrue(self.conf(first).is_symlink())
                self.assertFalse(self.conf(second).is_symlink())
                release = self.bundle / "current"
                self.assertIn(f"Environment=DIAMOND_CURSOR_SCROLL_{first.upper()}=1",
                              (release / f"{first}.conf").read_text())
                self.extra(second, "install")
                self.assertEqual(self.log.read_text().splitlines(), ["build"])
                self.extra(first, "uninstall")
                self.assertFalse(self.conf(first).is_symlink())
                self.assertTrue(self.conf(second).is_symlink())
                self.prepare()
                self.assertIn("LD_LIBRARY_PATH=", (self.root / "login.env").read_text())
                self.extra(second, "uninstall")
                self.extra(second, "uninstall")
                self.assertFalse(self.bundle.exists())

    def test_upgrade_fallback_then_rebuild(self):
        self.extra("speed", "install")
        old = (self.bundle / "current").resolve()
        with (self.etc / "os-release").open("a") as f:
            f.write("PRETTY_NAME=Ubuntu\n")
        result = self.prepare()
        self.assertIn("skipped", result.stderr)
        self.assertFalse((self.root / "login.env").exists())
        self.extra("flick", "install")
        self.assertFalse(old.exists())
        self.assertTrue(self.conf("speed").is_symlink())
        self.prepare()
        self.assertTrue((self.root / "login.env").is_file())

    def test_failures_preserve_other_extra_and_foreign_files(self):
        failure = self.root / "build-error"
        failure.touch()
        self.extra("flick", "install", success=False)
        self.assertFalse(self.conf("flick").is_symlink())
        failure.unlink()
        self.extra("flick", "install")
        (self.root / "reload-error").touch()
        self.extra("speed", "install", success=False)
        self.assertTrue(self.conf("flick").is_symlink())
        self.assertFalse(self.conf("speed").is_symlink())
        self.extra("flick", "uninstall", success=False)
        self.assertTrue(self.conf("flick").is_symlink())
        self.conf("speed").write_text("my own override")
        self.extra("speed", "install", success=False)
        self.assertEqual(self.conf("speed").read_text(), "my own override")

    def test_unsupported_install_but_removal_after_upgrade(self):
        self.extra("speed", "install")
        self.stub("dpkg-query", "echo '51.1 amd64'")
        self.assertIn("51.0-1ubuntu3", self.extra("flick", "install", success=False).stderr)
        self.extra("speed", "uninstall")
        self.assertFalse(self.bundle.exists())


if __name__ == "__main__":
    unittest.main()
