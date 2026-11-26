# Website and keyboard illustration

The [public site](https://cray0000.github.io/diamond-cursor/) builds from the main mapping table and clone instructions, the Linux and macOS guides, and the SVG keyboard map. Edit installation steps and optional extras in the platform READMEs. The site turns their Markdown headings into sections and expandable guides. Each third-level heading under **Optional extras** becomes an individual disclosure. The key inspector reads the Linux bindings during the build and checks the highlighted positions in the artwork.

## Preview locally

From the repository root, run the following commands with Python 3.10 or newer.

```sh
python3 -m venv /tmp/diamond-cursor-site
/tmp/diamond-cursor-site/bin/pip install --require-hashes -r site/requirements.txt
/tmp/diamond-cursor-site/bin/python site/build.py
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
