# Diamond Cursor for Linux

Hold **Left Alt** to use the arrow keys under your right hand. The diamond follows the physical US QWERTY key positions across layouts. For example, the QWERTY **J** key types `h` in Programmer Dvorak and `о` in standard Russian. Left Alt turns that same key into Left Arrow in all three layouts.

## Quick install on Ubuntu

From the repository root, run the installer.

```sh
./linux/install.sh
```

### What the installer changes

The script asks for sudo, reuses an existing `keyd` service or installs it from your configured APT repositories, and enables the mapping now and at boot. For Ubuntu releases before 25.04, see [Manual install](#manual-install) for the backport.

The installer also sets up touchpad pairing on a fresh install. Log out and back in, or reboot, for libinput to pick up the rule. If the installer reports an existing libinput override, follow [Touchpad pairing](#touchpad-pairing).

To undo it, run `./linux/uninstall.sh` from the repository root. Uninstall removes the standalone mapping and keeps `keyd` available for other configurations.

If you already have a wildcard `keyd` config or have edited `/etc/keyd/diamond.conf`, the script points you to the manual steps so you can keep your bindings.

## Bindings

| Hold | Physical key | Sends |
| --- | --- | --- |
| Left Alt | I | ↑ |
| Left Alt | J | ← |
| Left Alt | K | ↓ |
| Left Alt | L | → |
| Left Alt | U / M | Page Up / Page Down |
| Left Alt | H / apostrophe (`'`) | Backspace / Delete |
| Left Alt | semicolon (`;`) | Escape |
| Left Alt + Left Ctrl | J / L | Home / End |

Add **either Shift** to any binding to send the shifted key. In a text editor, Left Alt + Shift + L selects one character to the right. Left Alt + Left Ctrl + Shift + L selects to the end of the line. Shift + Delete and Shift + Backspace have their usual application-specific behavior.

## Manual install

Ubuntu includes `keyd` in its repositories starting with 25.04. On these releases, install it with APT. [Ubuntu package details](https://github.com/rvaiya/keyd#ubuntu)

```sh
sudo apt install keyd
```

For older Ubuntu releases, the project lists a [backport](https://github.com/rvaiya/keyd#ubuntu). You can also build from source. On other systemd-based distributions, use your package manager. Once the `keyd` service is available, choose the setup that fits your machine. [Upstream installation instructions](https://github.com/rvaiya/keyd#installation)

**Fresh setup.** Copy the config and start the service from the `linux/` directory in the cloned repository.

```sh
sudo install -D -m 0644 diamond.conf /etc/keyd/diamond.conf
sudo systemctl enable keyd.service
sudo systemctl restart keyd.service
```

**Existing setup.** Keep the `[ids]` section in the config that matches your keyboard. Merge the `[main]`, `[left_control:C]`, `[alt]`, and `[alt+left_control]` bindings from [diamond.conf](diamond.conf) into that file in the order shown, then run `sudo systemctl restart keyd.service`. Each keyboard uses one matching config.

Try holding **Left Alt + J** in a text editor. The cursor should keep moving left until you release J. Try **Left Alt + Shift + J** to select, then switch layouts and try the same physical keys again. If the mapping is inactive, the service log shows which config and keyboard the daemon loaded.

```sh
journalctl -u keyd.service -b --no-pager
```

### Touchpad pairing

On laptops, libinput normally pairs the built-in touchpad with the built-in keyboard for **disable while typing**. With Diamond Cursor, keystrokes reach the desktop through `keyd virtual keyboard`. The pairing rule identifies that device as internal so your desktop can honor its existing touchpad setting and delay. An external keyboard remapped by keyd can also trigger the delay because its events come from the same virtual device. [libinput documentation](https://wayland.freedesktop.org/libinput/doc/latest/palm-detection.html#disable-while-typing)

For a manual install, or if the installer kept an existing override, check `/etc/libinput/local-overrides.quirks`. If you already have a rule that matches the keyd keyboard and sets `AttrKeyboardIntegration=internal`, the pairing is set up. Otherwise, open the file and append the section from [keyd.quirks](keyd.quirks) below your existing sections. These commands also work on a fresh installation.

```sh
sudo mkdir -p /etc/libinput
sudoedit /etc/libinput/local-overrides.quirks
```

Log out and back in, or reboot. With **disable while typing** enabled in your desktop settings, type a few letters while brushing the touchpad. The pointer should stay still while you type and respond again after the delay. [Local libinput overrides](https://wayland.freedesktop.org/libinput/doc/latest/device-quirks.html#installing-temporary-local-device-quirks)

## Optional extras

Run these commands from the `linux/` directory. Each extra has its own install and uninstall commands and works independently of the Diamond Cursor bindings.

### 300 ms delay after typing

This extra sets GNOME’s **disable while typing** delay to 300 ms for your account. It takes effect immediately and persists across logins. The delay applies when **disable while typing** is enabled. If you use keyd, set up [touchpad pairing](#touchpad-pairing) first.

Run this in your GNOME session as your regular user. It needs the `disable-while-typing-timeout` setting, `gsettings`, and the `dconf` command (`dconf-cli` on Ubuntu).

```sh
./extras/typing-delay.sh install
```

To restore your previous delay, run the command below. If you chose a different delay after installation, uninstall keeps that choice.

```sh
./extras/typing-delay.sh uninstall
```

### 30 mm palm filter on both touchpad edges

This extra uses unpalm to ignore touches and light taps that **start** in the outer 30 mm on either side of your built-in touchpad. A swipe that starts in the middle continues tracking into both edges. A physical click can still register. On a 125 mm pad, the two strips leave 65 mm in the middle for starting swipes and taps. [How unpalm works](https://github.com/rpodgorny/unpalm/blob/v0.2.2/README.md#how-it-works)

```sh
./extras/palm-filter.sh install
```

The installer asks for sudo, reads the pad’s width from udev, and converts 30 mm into the percentage unpalm expects. It requires systemd, udev, kernel uinput support, and a touchpad with a stable `/dev/input/by-path/` link and a reported width greater than 60 mm. If automatic selection is ambiguous, run `./extras/palm-filter.sh install /dev/input/eventN` with the built-in pad’s event node. The installer remembers its stable path for future boots.

The script reuses an installed `unpalm` executable. On x86-64, it can also download the pinned v0.2.2 release with `curl` and verify its SHA-256 checksum. On other architectures, install unpalm with your package manager or from source first. If you already run a separate unpalm filter, you can keep using it. [Upstream installation instructions](https://github.com/rpodgorny/unpalm/blob/v0.2.2/README.md#installation)

The filter starts immediately and whenever the touchpad appears after boot. Check it with `systemctl status diamond-cursor-palm-filter.service`. To return to normal touchpad input and remove the extra from startup, run the command below. An existing system copy of unpalm stays installed.

```sh
./extras/palm-filter.sh uninstall
```

### Touchpad flick and stop

Check the [GNOME scroll requirements](#gnome-scroll-requirements) before installing. Install this extra if a two-finger scroll keeps coasting after you stop moving and lift your fingers. A deliberate flick still coasts. The filter passes intentional flicks straight through and delays the release of a settled scroll by 240 ms. It recognizes a flick from at least 8 scroll units of net movement in the last 80 ms, with a movement within 40 ms of release.

```sh
./extras/scroll-flick.sh install
```

To remove just the flick filter, run `./extras/scroll-flick.sh uninstall`.

### Touchpad scroll speed

Check the [GNOME scroll requirements](#gnome-scroll-requirements) before installing. This extra sets two-finger scrolling to **0.2× by default**. An explicit GNOME `scroll-speed` preference takes precedence. Mouse-wheel and pointer speed keep their own settings. You can install this on its own or combine it with the flick filter. When both are enabled, flick detection uses the original finger movement.

```sh
./extras/scroll-speed.sh install
```

After signing in, adjust the multiplier live. For example, `0.5` gives half speed and `1.0` gives full speed. Resetting the preference returns to the extra’s 0.2× preset.

```sh
gsettings set org.gnome.desktop.peripherals.touchpad scroll-speed 0.5
gsettings reset org.gnome.desktop.peripherals.touchpad scroll-speed
```

To remove just the speed extra, run `./extras/scroll-speed.sh uninstall`. Your explicit GNOME preference is preserved.

## GNOME scroll requirements

Run the scripts as your desktop user on **Ubuntu 26.10 amd64, Ubuntu GNOME Wayland session, Mutter package `51.0-1ubuntu3`**. These fixes use GNOME’s input pipeline in the signed-in desktop. They work independently of keyd and Unpalm. **Log out and back in once** after installing or uninstalling either extra. You can install both before signing out.

The first installation needs Python 3, `curl`, Bubblewrap, APT and an internet connection. It downloads checksum-verified Ubuntu source archives and build dependencies into a temporary directory, then compiles a private Clutter library. No sudo is required. The second extra reuses the build. Each extra has its own per-user GNOME Shell service override. Removing the last extra also removes the shared build. If an update changes the GNOME binaries, the next sign-in uses Ubuntu’s library. Rerun the installer for a compatible build. The [Mutter patch](extras/gnome-scroll/mutter-51.patch) follows the affected Clutter sources’ LGPL-2.0-or-later license. [Ubuntu Mutter source package](https://launchpad.net/ubuntu/+source/mutter/51.0-1ubuntu3)

## How it works

`keyd` reads Linux input events and emits key presses through a virtual keyboard. This happens before the desktop applies its text layout, so one config covers Wayland, X11, the graphical login screen, and Linux virtual consoles once the service is running. The `*` in `[ids]` matches built-in and external keyboards. [keyd documentation](https://github.com/rvaiya/keyd)

The `[alt]` layer handles Left Alt. Unmapped combinations such as Alt + Tab keep their usual behavior, and Right Alt remains available for AltGr. Left Ctrl has its own layer so only the physical **Left Ctrl** activates Home and End with Left Alt.

## Troubleshooting

### Terminal vi prints A, B, C, or D in Insert mode

This Vim behavior is independent of Diamond Cursor and `keyd`. On Ubuntu, `vi` can start Vim Tiny with `esckeys` turned off. It then reads a terminal arrow sequence as separate keystrokes in Insert mode, even when you press a physical arrow on a machine without Diamond Cursor.

Press **Esc** and run `:set esckeys?`. If Vim reports `noesckeys`, run `:set esckeys`, press **i**, and try a physical arrow again. To keep the fix for future sessions, add `set esckeys` to your `~/.vimrc`.

With `sudo vi`, the same command fixes the open session. For future sessions, add `set esckeys` to root’s Vim config (usually `/root/.vimrc`), or use `SUDO_EDITOR=vi sudoedit /path/to/file` to edit a protected file with your own Vim settings.

## Manual removal

To remove the standalone config, delete its file and restart the service.

```sh
sudo rm /etc/keyd/diamond.conf
sudo systemctl restart keyd.service
```

If you merged the bindings into an existing config, remove those bindings and restart the service. For immediate recovery, press the physical **Backspace + Escape + Enter** keys together to stop `keyd`.

`./uninstall.sh` removes the touchpad override when the whole file still matches the supplied [keyd.quirks](keyd.quirks). If you merged the rule or later added other device settings, remove just the `[Diamond Cursor keyd keyboard]` section with `sudoedit` to undo the pairing. You can keep it if you still use keyd for another keyboard config. Log out and back in, or reboot, to apply the removal.

## Tests

The [test instructions](test/README.md) cover installer behavior, the optional extras, and the physical key bindings. The tests run without sudo or access to the live keyboard or touchpad.
