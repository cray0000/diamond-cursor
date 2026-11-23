# Diamond cursor for Linux

Hold **Left Alt** to use the arrow keys under your right hand. The diamond follows the physical US QWERTY key positions across layouts. For example, the QWERTY **J** key types `h` in Programmer Dvorak and `о` in standard Russian. Left Alt turns that same key into Left Arrow in all three layouts.

## Quick install on Ubuntu

From the `linux/` directory in your clone, run the installer.

```sh
./install.sh
```

The script asks for sudo, reuses an existing `keyd` service or installs it from your configured APT repositories, and enables the mapping now and at boot. For Ubuntu releases before 25.04, see [Manual install](#manual-install) for the backport. From the repository root, use `./linux/install.sh`.

To undo it, run `./uninstall.sh` from the same `linux/` directory. Uninstall removes the standalone mapping and keeps `keyd` available for other configurations.

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

## How it works

`keyd` reads Linux input events and emits key presses through a virtual keyboard. This happens before the desktop applies its text layout, so one config covers Wayland, X11, the graphical login screen, and Linux virtual consoles once the service is running. The `*` in `[ids]` matches built-in and external keyboards. [keyd documentation](https://github.com/rvaiya/keyd)

The `[alt]` layer handles Left Alt. Unmapped combinations such as Alt + Tab keep their usual behavior, and Right Alt remains available for AltGr. Left Ctrl has its own layer so only the physical **Left Ctrl** activates Home and End with Left Alt.

## Manual removal

To remove the standalone config, delete its file and restart the service.

```sh
sudo rm /etc/keyd/diamond.conf
sudo systemctl restart keyd.service
```

If you merged the bindings into an existing config, remove those bindings and restart the service. For immediate recovery, press the physical **Backspace + Escape + Enter** keys together to stop `keyd`.

## Tests

The [test instructions](test/README.md) cover installer behavior and the physical key bindings. Both suites run without sudo or access to the live keyboard.
