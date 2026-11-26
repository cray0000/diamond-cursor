# Diamond Cursor for macOS

This Karabiner-Elements configuration includes the cursor diamond, editing keys, and Shift selection. Start with the [mapping table](../README.md#mappings) for the physical key positions.

## Install

1. Install Karabiner-Elements, open its settings, and grant the permissions it requests. [Karabiner setup](https://karabiner-elements.pqrs.org/docs/getting-started/installation/)
2. If you already use Karabiner, save a copy of `~/.config/karabiner/karabiner.json` somewhere you can find it again. This config replaces all profiles in that file.
3. From the repository root, copy the file as your normal user. The copy command prompts before overwriting an existing file.

   ```sh
   mkdir -p ~/.config/karabiner
   cp -i macos/karabiner.json ~/.config/karabiner/karabiner.json
   ```

4. Open **Karabiner-Elements Settings → Profiles** and select a profile. In a text editor, try holding the diamond modifier and tapping **J** to move left, then add **Shift** to select.

## Profiles

| Profile | Use it for | Physical diamond modifier |
| --- | --- | --- |
| **Universal** (default) | Switching between the built-in Apple keyboard and an external keyboard. It recognizes Apple keyboard product IDs 611 and 641. | Left Command on those two devices, Left Option on other keyboards |
| **Keyboard** | A standard external keyboard or a US-layout MacBook using its labeled Option key | Left Option |
| **MacBook EU** | The EU MacBook layout with US-style punctuation and Enter placement | Left Command |

`MacBook EU` swaps the physical Return and backslash keys and remaps the ISO and grave-accent keys. `Universal` applies these punctuation and Return changes only to Apple product ID 611. The profiles also include modifier, Tab-switching, and function-row preferences. [Full Karabiner configuration](karabiner.json)

## Line navigation

All three profiles map physical Left Ctrl to Command. When you hold it with the diamond modifier and press **J** or **L**, the arrow rule accepts the extra modifier and sends **⌘←** or **⌘→**. Most Mac text editors use these shortcuts for the start or end of the line. The JSON also contains explicit Home/End rules lower in the list. Karabiner uses the first matching rule. [Karabiner rule priority](https://karabiner-elements.pqrs.org/docs/json/complex-modifications-manipulator-evaluation-priority/)

## Restore your previous profiles

Copy your saved configuration back to `~/.config/karabiner/karabiner.json`, then choose your previous profile in Karabiner-Elements Settings. [Karabiner configuration file location](https://karabiner-elements.pqrs.org/docs/manual/misc/configuration-file-path/)
