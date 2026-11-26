"""Build GitHub Pages from the repository guides and physical keyboard map."""
import configparser
from dataclasses import dataclass, field
from hashlib import sha256
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
STYLESHEET_VERSION = sha256((SITE / "style.css").read_bytes()).hexdigest()[:12]
REPO = "https://github.com/" + os.environ.get("GITHUB_REPOSITORY", "cray0000/diamond-cursor")
BRANCH = os.environ.get("GITHUB_REF_NAME", "master")
GUIDES = {"": ROOT / "README.md", "linux": ROOT / "linux/README.md", "macos": ROOT / "macos/README.md"}
MD = MarkdownIt("commonmark", {"html": False}).enable("table")


def slug(title):
    return re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-")


def anchor(platform, section):
    return "-".join(filter(None, (platform, section))) or "top"


def resolve_link(url, platform, routes):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return url
    current = GUIDES[platform]
    target = (current.parent / unquote(parsed.path)).resolve() if parsed.path else current
    for name, path in GUIDES.items():
        if target == path or (parsed.path and target == path.parent):
            return routes[anchor(name, parsed.fragment)] if parsed.fragment else f"{name or 'index'}.html"
    if not target.exists():
        raise ValueError(f"Broken link in {current}: {url}")
    return f"{REPO}/blob/{BRANCH}/{target.relative_to(ROOT)}" + ("#" + parsed.fragment if parsed.fragment else "")


def template(name, **values):
    return Template((SITE / name).read_text()).substitute(values)


def walk(section):
    yield section
    for child in section.children:
        yield from walk(child)


def render(tokens):
    return MD.renderer.render(tokens, MD.options, {})


@dataclass
class Section:
    title: str
    id: str
    body: list = field(default_factory=list)
    children: list = field(default_factory=list)

    def child(self, name):
        for section in self.children:
            if section.id == name:
                return section
        raise ValueError(f"Missing README heading {name!r} under {self.title!r}")

    def content(self):
        return render(self.body)

    def command(self):
        blocks = [token.content.rstrip() for token in self.body if token.type == "fence" and token.info == "sh"]
        if len(blocks) != 1:
            raise ValueError(f"Expected a single shell block under {self.title}")
        return blocks[0]


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
        stack[-1][1].body.append(token)
        i += 1
    return root.children[0]


def sections_html(sections, level=2):
    parts = []
    for section in sections:
        tag = f"h{level}"
        parts.append(f'<section id="{section.id}"><{tag}>{escape(section.title)}</{tag}>'
                     f'{section.content()}{sections_html(section.children, level + 1)}</section>')
    return "".join(parts)


def contents(sections):
    if not sections:
        return ""
    links = "".join(f'<a href="#{section.id}">{escape(section.title)}</a>' for section in sections)
    return f'<nav class="contents" aria-label="On this page"><strong>On this page</strong>{links}</nav>'


def anchor_link(url, title):
    return f'<a href="{escape(url)}">{escape(title)}</a>'


def docs_navigation(current, tools):
    def link(url, label):
        state = ' aria-current="page"' if url == current else ""
        return f'<a href="{escape(url)}"{state}>{escape(label)}</a>'

    guides = (("./", "Project overview"), ("bindings.html", "Key reference"),
              ("linux.html", "Linux guide"), ("macos.html", "macOS guide"))
    pages = "".join(f"<li>{link(url, label)}</li>" for url, label in guides)
    utilities = "".join(f"<li>{link(tool.id + '.html', tool.title)}</li>" for tool in tools)
    overview = link("touchpad.html", "Linux touchpad tools")
    return f'<ul class="doc-pages">{pages}<li>{overview}<ul>{utilities}</ul></li></ul>'


def document(filename, *, tools, title, heading_id, intro, body, description, sections=(), parents=(), related=""):
    trail = [anchor_link("./", "Diamond Cursor"), *(anchor_link(url, name) for url, name in parents)]
    trail.append(f'<span aria-current="page">{escape(title)}</span>')
    content = template("guide.html", navigation=docs_navigation(filename, tools),
                       breadcrumbs='<span aria-hidden="true">/</span>'.join(trail),
                       heading=escape(title), anchor=heading_id, intro=intro, body=body,
                       contents=contents(sections), related=related)
    write_page(filename, title + " · Diamond Cursor", description, content)


def write_page(filename, title, description, content, home="./", scripts=""):
    page = template("page.html", title=escape(title), description=escape(description), content=content,
                    repo=escape(REPO), home=home, scripts=scripts, stylesheet_version=STYLESHEET_VERSION)
    (DIST / filename).write_text(page)


def first_paragraph(section):
    end = next(i for i, token in enumerate(section.body) if token.type == "paragraph_close")
    return render(section.body[:end + 1]), render(section.body[end + 1:])


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


def markdown_links(section):
    for token in section.body:
        for item in token.children or []:
            if item.type == "link_open":
                yield item


def link_guides(guides, extras, requirements):
    routes = {"quick-install": "index.html#setup", "mappings": "bindings.html#mappings"}
    for platform in ("linux", "macos"):
        for section in walk(guides[platform]):
            routes[section.id] = f"{platform}.html#{section.id}"
    routes[extras.id] = "touchpad.html#" + extras.id
    needs_requirements = set()
    for tool in extras.children:
        url = f"{tool.id}.html"
        for section in walk(tool):
            routes[section.id] = f"{url}#{section.id}"
        if any(item.attrGet("href") == "#gnome-scroll-requirements" for item in markdown_links(tool)):
            needs_requirements.add(tool.id)
    # Shared compatibility notes are included on each scroll tool's page.
    # Older bookmarks for the standalone section open the first matching page.
    first_scroll = next((tool for tool in extras.children if tool.id in needs_requirements), None)
    routes[requirements.id] = f"{first_scroll.id}.html#{requirements.id}" if first_scroll else routes[extras.id]

    for platform, guide in guides.items():
        for section in walk(guide):
            for item in markdown_links(section):
                url = item.attrGet("href")
                if section.id in needs_requirements and url == "#gnome-scroll-requirements":
                    item.attrSet("href", "#" + requirements.id)
                else:
                    item.attrSet("href", resolve_link(url, platform, routes))

    return routes, needs_requirements


def home_page(guides, routes):
    linux = guides["linux"]
    mac_install = guides["macos"].child("macos-install")
    clone = guides[""].child("quick-install").command()

    def commands(section):
        lines = [*clone.splitlines(), *section.command().splitlines()]
        code = "\n".join(f'<span class="command-line">{escape(line)}</span>' for line in lines)
        return f"<pre><code>{code}</code></pre>"

    svg = (ROOT / "assets/keyboard-map.svg").read_text()
    index = template("index.html", diagram=svg, keys=key_actions(svg), previous_links=json.dumps(routes),
                     edit_demo=template("edit-demo.html", standard=template("edit-keyboard.svg", method="standard"),
                                        diamond=template("edit-keyboard.svg", method="diamond")),
                     linux_commands=commands(linux.child("linux-quick-install-on-ubuntu")),
                     linux_practice=template("practice.html", platform="linux", modifier="<kbd>Left Alt</kbd>"),
                     mac_prepare=mac_install.child("macos-prepare-karabiner-elements").content(),
                     mac_commands=commands(mac_install.child("macos-copy-the-configuration")),
                     mac_activate=mac_install.child("macos-choose-the-universal-profile").content(),
                     mac_practice=template("practice.html", platform="macos", modifier="the key beside Space"))
    write_page("index.html", "Diamond Cursor · Keyboard navigation for Linux and macOS",
               "Move and select text with the physical I/J/K/L diamond. Explore the map and install on Linux or macOS.",
               index, home="", scripts='<script src="ui.js" defer></script><script src="edit-demo.js" defer></script>')


def key_reference(bindings, tools):
    document("bindings.html", tools=tools, title="Key reference", heading_id=bindings.id, intro="",
             body=bindings.content(), description="The physical cursor, selection, and editing shortcuts on Linux and macOS.",
             related='<p class="related"><a href="./#setup">Install Diamond Cursor</a></p>')


def platform_guides(guides, extras, requirements):
    for platform, label in (("linux", "Linux"), ("macos", "macOS")):
        guide = guides[platform]
        sections = [s for s in guide.children if s not in (extras, requirements)]
        related = f'<p class="related"><a href="./#{platform}">Back to quick setup</a></p>'
        if platform == "linux":
            related += ('<aside class="related-tools"><h2>Also in this repository</h2>'
                        '<a href="touchpad.html">Optional Linux touchpad tools</a>'
                        '<p>Adjust palm rejection, the delay after typing, or two-finger scrolling independently.</p></aside>')
        document(f"{platform}.html", tools=extras.children, title=f"{label} guide", heading_id=guide.id, intro=guide.content(),
                 body=sections_html(sections), sections=sections, related=related,
                 description=f"Install, configure, and remove Diamond Cursor on {label}.")


def touchpad_guides(extras, requirements, needs_requirements):
    descriptions = {
        "linux-300-ms-delay-after-typing": "Resume using the touchpad sooner after typing.",
        "linux-30-mm-palm-filter-on-both-touchpad-edges": "Ignore touches that start along the side edges.",
        "linux-touchpad-flick-and-stop": "Stop coasting when you lift your fingers after pausing.",
        "linux-touchpad-scroll-speed": "Slow down two-finger scrolling while keeping mouse-wheel speed.",
    }
    links = []
    for tool in extras.children:
        lead, instructions = first_paragraph(tool)
        description = descriptions.get(tool.id, tool.title)
        filename = f"{tool.id}.html"
        links.append(f'<li><a href="{filename}"><strong>{escape(tool.title)}</strong>'
                     f'<span>{escape(description)}</span></a></li>')
        body = '<p>From your clone of the repository, open the <code>linux/</code> directory in a terminal.</p>'
        if tool.id in needs_requirements:
            compatibility, build_notes = first_paragraph(requirements)
            body += f'<section id="{requirements.id}"><h2>Check compatibility</h2>{compatibility}</section>'
        body += f'<section><h2>Install and remove</h2>{instructions}{sections_html(tool.children, 3)}</section>'
        if tool.id in needs_requirements:
            body += f'<section><h2>How the build works</h2>{build_notes}</section>'
        document(filename, tools=extras.children, title=tool.title, heading_id=tool.id, intro=lead, description=description, body=body,
                 parents=(("touchpad.html", "Touchpad tools"),),
                 related='<p class="related"><a href="touchpad.html">All touchpad tools</a></p>')
    document("touchpad.html", tools=extras.children, title="Linux touchpad tools", heading_id=extras.id,
             intro="<p>Choose the touchpad behavior you want to change. Each tool installs and uninstalls independently of the keyboard mapping.</p>",
             description="Optional touchpad utilities for Linux laptops.", parents=(("linux.html", "Linux guide"),),
             body='<ul class="tool-list">' + "".join(links) + "</ul>")


def build():
    DIST.mkdir(exist_ok=True)
    guides = {platform: read_guide(platform) for platform in GUIDES}
    linux = guides["linux"]
    extras = linux.child("linux-optional-extras")
    requirements = linux.child("linux-gnome-scroll-requirements")

    routes, needs_requirements = link_guides(guides, extras, requirements)
    home_page(guides, routes)
    key_reference(guides[""].child("mappings"), extras.children)
    platform_guides(guides, extras, requirements)
    touchpad_guides(extras, requirements, needs_requirements)
    for name in ("style.css", "ui.js", "edit-demo.js", "copy.js", "mark.svg"):
        shutil.copy2(SITE / name, DIST)
    shutil.copytree(SITE / "fonts", DIST / "fonts", dirs_exist_ok=True)


if __name__ == "__main__":
    build()
