"""Check internal links and old single-page bookmarks in the built Pages site."""
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

DIST = Path(__file__).resolve().parent / "dist"


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.ids = set()
        self.links = []
        self.bookmarks = False
        self.in_docs_nav = False
        self.doc_menus = []
        self.feed(path.read_text())

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        element_id = attrs.get("id")
        if element_id:
            assert element_id not in self.ids, f"Duplicate ID: {element_id}"
            self.ids.add(element_id)
        if tag == "script" and element_id == "previous-links":
            self.bookmarks = True
        if tag == "nav":
            self.in_docs_nav = attrs.get("aria-label") == "Documentation"
        if self.in_docs_nav:
            if tag == "ul" and "doc-pages" in attrs.get("class", "").split():
                self.doc_menus.append([])
            if tag == "a":
                self.doc_menus[-1].append((attrs["href"], attrs.get("aria-current")))
        for key in ("href", "src"):
            if attrs.get(key):
                self.links.append(attrs[key])

    def handle_data(self, data):
        if self.bookmarks:
            self.links.extend(json.loads(data).values())

    def handle_endtag(self, tag):
        if tag == "script":
            self.bookmarks = False
        if tag == "nav":
            self.in_docs_nav = False


if __name__ == "__main__":
    pages = {path: Page(path) for path in DIST.glob("*.html")}
    assert DIST / "index.html" in pages, "Build the site before checking links."
    destinations = {"./" if p.name == "index.html" else p.name for p in pages}
    for path, page in pages.items():
        assert bool(page.doc_menus) == (path.name != "index.html"), path.name
        for menu in page.doc_menus:
            assert {url for url, _ in menu} == destinations, f"Incomplete documentation menu on {path.name}"
            assert [url for url, state in menu if state == "page"] == [path.name], path.name
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if target.is_dir():
                target /= "index.html"
            assert target.is_relative_to(DIST) and target.is_file(), f"{path.name}: {link}"
            if target in pages and url.fragment:
                assert unquote(url.fragment) in pages[target].ids, f"{path.name}: {link}"
    print(f"Internal links and bookmarks passed across {len(pages)} pages.")
