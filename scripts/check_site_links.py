#!/usr/bin/env python3
"""Check the static site for missing repository-local links and HTML anchors."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = (ROOT / "index.html", ROOT / "knowledge-base.html")


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("href"):
            self.links.append(values["href"] or "")
        if values.get("id"):
            self.ids.add(values["id"] or "")
        if tag == "a" and values.get("name"):
            self.ids.add(values["name"] or "")


def inspect(path: Path) -> LinkParser:
    parser = LinkParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def main() -> int:
    parsers = {page.resolve(): inspect(page) for page in PAGES}
    problems: list[str] = []
    checked = 0
    for page, parser in parsers.items():
        for href in parser.links:
            url = urlsplit(href)
            if url.scheme or href.startswith("//"):
                continue
            target = (page.parent / unquote(url.path)).resolve() if url.path else page
            if not target.exists():
                problems.append(f"{page.relative_to(ROOT)}: missing target {href!r}")
                continue
            checked += 1
            if url.fragment and target.suffix.lower() == ".html":
                target_parser = parsers.get(target)
                if target_parser is None:
                    try:
                        target_parser = inspect(target)
                    except (OSError, UnicodeDecodeError) as exc:
                        problems.append(f"{page.relative_to(ROOT)}: cannot inspect {href!r}: {exc}")
                        continue
                    parsers[target] = target_parser
                if unquote(url.fragment) not in target_parser.ids:
                    problems.append(f"{page.relative_to(ROOT)}: missing anchor {href!r}")
    if problems:
        print("Site link check failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"Site link check passed: {checked} repository-local links resolved across {len(PAGES)} site pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
