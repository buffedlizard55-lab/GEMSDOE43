import html.parser
import pathlib
import unittest
from urllib.parse import unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class LinkCollector(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self.ids = set()
        self.download_links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        href = attributes.get("href")
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if href:
            self.hrefs.append(href)
        if tag == "a" and href and "download" in attributes:
            self.download_links.append(href)


class SiteTests(unittest.TestCase):
    def test_legacy_pages_root_redirects_to_documented_landing_page(self):
        root_entry = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("docs/index.html", root_entry)
        self.assertTrue((DOCS / "index.html").is_file())

    def test_relative_links_resolve_within_the_site(self):
        for page in sorted(DOCS.glob("*.html")):
            parser = LinkCollector()
            parser.feed(page.read_text(encoding="utf-8"))
            for href in parser.hrefs:
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = (page.parent / unquote(parsed.path)).resolve()
                self.assertTrue(target.is_relative_to(DOCS.resolve()), f"site link escapes docs: {page.name} -> {href}")
                self.assertTrue(target.exists(), f"broken local link in {page.name}: {href}")
                if parsed.fragment:
                    fragment_page = page if not parsed.path else target
                    fragment_parser = LinkCollector()
                    fragment_parser.feed(fragment_page.read_text(encoding="utf-8"))
                    self.assertIn(parsed.fragment, fragment_parser.ids,
                                  f"broken fragment in {page.name}: {href}")

    def test_failed_candidate_is_not_offered_as_a_download(self):
        landing = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertIn("No eligible submission download", landing)
        self.assertIn("failed the preregistered promotion gate", landing)
        for page in DOCS.glob("*.html"):
            parser = LinkCollector()
            parser.feed(page.read_text(encoding="utf-8"))
            self.assertEqual(parser.download_links, [], f"download attribute must not expose a failed candidate: {page.name}")
        self.assertFalse(any(DOCS.glob("downloads/*.tif")), "a failed candidate must not be shipped as a submission")


if __name__ == "__main__":
    unittest.main()
