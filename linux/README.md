# Diamond cursor for Linux

Hold **Left Alt** to use the arrow keys under your right hand. The diamond follows the physical US QWERTY key positions across layouts. For example, the QWERTY **J** key types `h` in Programmer Dvorak and `о` in standard Russian. Left Alt turns that same key into Left Arrow in all three layouts.

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

## Installation

On Ubuntu releases that package `keyd`, install it with APT. On another systemd-based Linux distribution, use its package manager or follow the [upstream installation instructions](https://github.com/rvaiya/keyd#installation).

```sh
sudo apt install keyd
```

For a fresh `keyd` setup, run these commands from the root of the cloned repository.

```sh
sudo install -D -m 0644 linux/diamond.conf /etc/keyd/diamond.conf
sudo systemctl enable keyd.service
sudo systemctl restart keyd.service
```

If you already use `keyd`, merge the layer bindings from [diamond.conf](diamond.conf) into the config that matches your keyboard. Each keyboard uses one matching config, so two files that both match `*` can compete.

Try holding **Left Alt + J** in a text editor. The cursor should keep moving left until you release J. Try **Left Alt + Shift + J** to select, then switch layouts and try the same physical keys again. If the mapping is inactive, the service log shows which config and keyboard the daemon loaded.

```sh
journalctl -u keyd.service -b --no-pager
```

## How it works

`keyd` reads Linux input events and emits key presses through a virtual keyboard. This happens before the desktop applies its text layout, so one config covers Wayland, X11, the graphical login screen, and Linux virtual consoles once the service is running. The `*` in `[ids]` matches built-in and external keyboards. [keyd documentation](https://github.com/rvaiya/keyd)

The `[alt]` layer handles Left Alt. Unmapped combinations such as Alt + Tab keep their usual behavior, and Right Alt remains available for AltGr. Left Ctrl has its own layer so only the physical **Left Ctrl** activates Home and End with Left Alt.

## Removal

To remove the standalone config, delete its file and restart the service.

```sh
sudo rm /etc/keyd/diamond.conf
sudo systemctl restart keyd.service
```

If you merged the bindings into an existing config, remove those bindings and restart the service. For immediate recovery, press the physical **Backspace + Escape + Enter** keys together to stop `keyd`.
