"""Build GitHub Pages from the repository guides and physical keyboard map."""
import configparser
from dataclasses import dataclass, field
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
from string import Template
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent
DIST = SITE / "dist"
REPO = "https://github.com/" + os.environ.get("GITHUB_REPOSITORY", "cray0000/diamond-cursor")
BRANCH = os.environ.get("GITHUB_REF_NAME", "master")
GUIDES = {"": ROOT / "README.md", "linux": ROOT / "linux/README.md", "macos": ROOT / "macos/README.md"}
MD = MarkdownIt("commonmark", {"html": False}).enable("table")


def slug(title):
    return re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-")


def anchor(platform, section):
    return "-".join(filter(None, (platform, section))) or "top"


def resolve_link(url, platform):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return url
    current = GUIDES[platform]
    target = (current.parent / unquote(parsed.path)).resolve() if parsed.path else current
    for name, path in GUIDES.items():
        if target in (path, path.parent) and (target == path or parsed.path):
            return "#" + anchor(name, parsed.fragment)
    if not target.exists():
        raise ValueError(f"Broken link in {current}: {url}")
    return f"{REPO}/blob/{BRANCH}/{target.relative_to(ROOT)}" + ("#" + parsed.fragment if parsed.fragment else "")


@dataclass
class Section:
    title: str
    id: str
    body: list = field(default_factory=list)
    children: list = field(default_factory=list)

    def child(self, name):
        return next(x for x in self.children if x.id == name)

    def content(self):
        return MD.renderer.render(self.body, MD.options, {})


def read_guide(platform):
    tokens = MD.parse(GUIDES[platform].read_text())
    root = Section("", "")
    stack = [(0, root)]
    ids = set()
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open":
            title = tokens[i + 1].content
            level = int(token.tag[1:])
            while stack[-1][0] >= level:
                stack.pop()
            section = Section(title, anchor(platform, slug(title)))
            if section.id in ids:
                raise ValueError(f"Duplicate heading in {GUIDES[platform]}: {title}")
            ids.add(section.id)
            stack[-1][1].children.append(section)
            stack.append((level, section))
            i += 3
            continue
        for item in token.children or []:
            if item.type == "link_open":
                item.attrSet("href", resolve_link(item.attrGet("href"), platform))
        stack[-1][1].body.append(token)
        i += 1
    return root.children[0]


def body_with_children(section):
    html = section.content()
    for child in section.children:
        html += disclosure(child)
    return html


def disclosure(section):
    return (f'<details class="disclosure" id="{section.id}"><summary>{escape(section.title)}</summary>'
            f'<div class="prose drawer">{body_with_children(section)}</div></details>')


def panel(platform, name):
    guide = read_guide(platform)
    install = guide.children[0]
    sections = []
    for item in guide.children:
        if item == install:
            continue
        if item.id == "linux-optional-extras":
            cards = "".join(disclosure(child) for child in item.children)
            sections.append(f'<section class="extras" id="{item.id}"><h3>{escape(item.title)}</h3>'
                            f'<div class="prose">{item.content()}</div>{cards}</section>')
        else:
            sections.append(disclosure(item))
    return (f'<article class="panel" id="{platform}" aria-label="{name} guide">'
            f'<div class="guide-intro prose">{guide.content()}</div>'
            f'<div class="quick" id="{install.id}"><h3>{escape(install.title)}</h3>'
            f'<div class="prose">{body_with_children(install)}</div></div>{"".join(sections)}</article>')


def key_actions(svg):
    config = configparser.ConfigParser(interpolation=None, allow_no_value=True)
    config.read(ROOT / "linux/diamond.conf")
    actions = {"up": "Move up", "left": "Move left", "down": "Move down", "right": "Move right",
               "pageup": "Page up", "pagedown": "Page down", "backspace": "Backspace",
               "delete": "Forward delete", "esc": "Escape"}
    keys = {key: {"label": {"semicolon": ";", "apostrophe": "'"}.get(key, key.upper()),
                  "action": actions[value]} for key, value in config["alt"].items()}
    for key, value in config["alt+left_control"].items():
        keys[key]["ctrl"] = {"home": "Line start", "end": "Line end"}[value]
    if set(re.findall(r'data-key="([^"]+)"', svg)) != set(keys):
        raise ValueError("The SVG key positions and the keyd layer disagree.")
    return json.dumps(keys, ensure_ascii=False).replace("<", "\\u003c")


def build():
    guide = read_guide("")
    svg = (ROOT / "assets/keyboard-map.svg").read_text()
    values = dict(repo=escape(REPO), diagram=svg, keys=key_actions(svg),
                  clone=guide.child("quick-install").content(), mappings=guide.child("mappings").content(),
                  linux=panel("linux", "Linux"), macos=panel("macos", "macOS"))
    page = Template((SITE / "index.html").read_text()).substitute(values)
    DIST.mkdir(exist_ok=True)
    (DIST / "index.html").write_text(page)
    for name in ("style.css", "ui.js", "mark.svg"):
        shutil.copy2(SITE / name, DIST)
    shutil.copytree(SITE / "fonts", DIST / "fonts", dirs_exist_ok=True)


if __name__ == "__main__":
    build()
