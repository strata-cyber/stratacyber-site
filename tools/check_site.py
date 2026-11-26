#!/usr/bin/env python3
"""Checks the built site in dist/ before it is published. Standard library only.

    python build.py && python tools/check_site.py

Fails (exit 1) on:
- internal links, images, scripts or stylesheets that point to a file that does not exist
- #anchors that do not exist on the target page
- images without alt text
- pages missing <html lang>, <title>, meta description, canonical, Content-Security-Policy or og:image
- hreflang alternates that are not reciprocal (page A lists B, but B does not list A)
- sitemap entries that do not exist in dist/
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def site_url() -> str:
    import tomllib
    return tomllib.loads((ROOT / "site.toml").read_text("utf-8"))["url"].rstrip("/")


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.refs: list[tuple[str, str]] = []  # (tag, url)
        self.imgs_without_alt: list[str] = []
        self.lang = ""
        self.title = False
        self.meta: dict[str, str] = {}
        self.canonical = ""
        self.alternates: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "title":
            self.title = True
        elif tag == "meta":
            key = a.get("name") or a.get("property") or a.get("http-equiv")
            if key:
                self.meta[key.lower()] = a.get("content", "")
        elif tag == "link":
            rel = a.get("rel", "")
            if rel == "canonical":
                self.canonical = a.get("href", "")
            elif rel == "alternate" and "hreflang" in a:
                self.alternates[a["hreflang"]] = a.get("href", "")
            elif rel not in ("alternate", "preconnect", "dns-prefetch"):
                self.refs.append((tag, a.get("href", "")))
        elif tag == "img":
            self.refs.append((tag, a.get("src", "")))
            if not a.get("alt", "").strip():
                self.imgs_without_alt.append(a.get("src", ""))
        elif tag == "script" and "src" in a:
            self.refs.append((tag, a["src"]))
        elif tag in ("a", "area") and "href" in a:
            self.refs.append((tag, a["href"]))
        elif tag == "use" and "href" in a:
            self.refs.append((tag, a["href"]))


def target_file(url_path: str) -> Path:
    p = DIST / unquote(url_path).lstrip("/")
    if url_path.endswith("/") or p.is_dir():
        p = p / "index.html"
    return p


def main() -> int:
    if not (DIST / "index.html").exists():
        print("dist/ is empty: run python build.py first", file=sys.stderr)
        return 1
    base = site_url()
    errors: list[str] = []
    pages: dict[Path, Page] = {}
    for f in sorted(DIST.rglob("*.html")):
        p = Page()
        p.feed(f.read_text("utf-8"))
        pages[f] = p

    def page_path(f: Path) -> str:
        rel = "/" + f.relative_to(DIST).as_posix()
        return rel.removesuffix("index.html")

    for f, p in pages.items():
        here = page_path(f)
        where = f.relative_to(DIST).as_posix()
        for k in ("description", "content-security-policy", "og:image"):
            if not p.meta.get(k):
                errors.append(f"{where}: missing meta {k}")
        if not p.lang:
            errors.append(f"{where}: missing <html lang>")
        if not p.title:
            errors.append(f"{where}: missing <title>")
        if not p.canonical and f.name != "404.html":
            errors.append(f"{where}: missing canonical link")
        for src in p.imgs_without_alt:
            errors.append(f"{where}: image without alt text: {src}")
        for tag, url in p.refs:
            if not url or url.startswith(("mailto:", "tel:", "data:")):
                continue
            parts = urlsplit(url)
            if parts.scheme in ("http", "https"):
                if not url.startswith(base):
                    continue  # external: not checked here
                parts = urlsplit(url[len(base):] or "/")
            elif parts.scheme:
                errors.append(f"{where}: unexpected URL scheme in <{tag}>: {url}")
                continue
            path = parts.path
            if not path:
                tf = f
            else:
                if not path.startswith("/"):
                    path = here.rsplit("/", 1)[0] + "/" + path
                tf = target_file(path)
                if not tf.exists():
                    errors.append(f"{where}: <{tag}> points to a missing file: {url}")
                    continue
            if parts.fragment and tf.suffix == ".html":
                target = pages.get(tf)
                if target is not None and parts.fragment not in target.ids:
                    errors.append(f"{where}: anchor #{parts.fragment} not found in {tf.relative_to(DIST).as_posix()}")
            elif parts.fragment and tf.suffix == ".svg":
                if f'id="{parts.fragment}"' not in tf.read_text("utf-8"):
                    errors.append(f"{where}: #{parts.fragment} not found in {tf.relative_to(DIST).as_posix()}")
        # hreflang must be reciprocal and point to existing pages.
        for lang, href in p.alternates.items():
            if not href.startswith(base):
                errors.append(f"{where}: hreflang {lang} is not on this site: {href}")
                continue
            tf = target_file(urlsplit(href[len(base):] or "/").path)
            other = pages.get(tf)
            if other is None:
                errors.append(f"{where}: hreflang {lang} points to a missing page: {href}")
            elif lang != "x-default" and base + here not in other.alternates.values():
                errors.append(f"{where}: hreflang {lang} -> {href} does not link back")

    sitemap = (DIST / "sitemap.xml").read_text("utf-8")
    for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap):
        if not loc.startswith(base) or not target_file(urlsplit(loc[len(base):]).path).exists():
            errors.append(f"sitemap.xml: entry does not exist in dist/: {loc}")

    for err in errors:
        print(f"error: {err}", file=sys.stderr)
    print(f"checked {len(pages)} page(s): {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
