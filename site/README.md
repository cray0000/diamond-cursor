# Website and keyboard illustration

The [public site](https://cray0000.github.io/diamond-cursor/) opens with the interactive key map and a quick install for Linux or macOS. The quick start combines the clone command from the main README with the install commands from the platform guides. The editable practice line receives keystrokes from the visitor’s operating system.

The homepage animation uses one edit script for both keyboards. [edit-demo.js](edit-demo.js) drives the text, selection, key highlights, and hand positions together. The typing cadence is shared, with extra time for the illustrated hand to travel between distant keys.

Edit the Markdown guides to update setup commands, key bindings, or detailed instructions. The build publishes the mapping table as the key reference. Each platform gets a standalone guide. Third-level sections under **Optional extras** in the Linux README get individual touchpad-tool pages and appear automatically in the shared documentation menu. An extra that links to **GNOME scroll requirements** includes those shared notes with its instructions. The homepage sets its own reading order while using the same command blocks as the guides.

## Preview locally

From the repository root, run the following commands with Python 3.10 or newer.

```sh
python3 -m venv /tmp/diamond-cursor-site
/tmp/diamond-cursor-site/bin/pip install --require-hashes -r site/requirements.txt
/tmp/diamond-cursor-site/bin/python site/build.py
python3 site/test_links.py
python3 -m http.server --bind 127.0.0.1 --directory site/dist 8000
```

Visit [the local preview](http://127.0.0.1:8000) and rebuild after editing. The generated files live in the Git-ignored `site/dist/` directory.

## Update the keyboard map

Edit [the vector artwork](../assets/keyboard-map.svg). Keep the highlighted groups’ `data-key` values in sync with the physical key names in [diamond.conf](../linux/diamond.conf). The site embeds the SVG and the repository README displays a double-resolution PNG. To regenerate the PNG, run the render script from the repository root.

```sh
./scripts/render-keyboard.sh
```

The renderer uses `rsvg-convert` (Ubuntu package `librsvg2-bin`, Homebrew package `librsvg`). Install DejaVu Sans and DejaVu Sans Mono for matching labels (Ubuntu package `fonts-dejavu-core`). Commit the SVG and PNG together.

## Deploy

In the GitHub repository, choose **Settings → Pages → Build and deployment → Source → GitHub Actions**. Each push to `master` runs the [Pages workflow](../.github/workflows/pages.yml) and publishes the generated artifact. You can also run **Publish website** manually in the Actions tab.
