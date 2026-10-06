import hashlib
import html.parser
import json
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


def page_links(page):
    parser = LinkCollector()
    parser.feed(page.read_text(encoding="utf-8"))
    return parser


class SiteTests(unittest.TestCase):
    def test_legacy_pages_root_redirects_to_documented_landing_page(self):
        root_entry = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("docs/index.html", root_entry)
        self.assertTrue((DOCS / "index.html").is_file())

    def test_relative_links_resolve_within_the_site(self):
        for page in sorted(DOCS.glob("*.html")):
            parser = page_links(page)
            for href in parser.hrefs:
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = (page.parent / unquote(parsed.path)).resolve()
                self.assertTrue(target.is_relative_to(DOCS.resolve()), f"site link escapes docs: {page.name} -> {href}")
                self.assertTrue(target.exists(), f"broken local link in {page.name}: {href}")
                if parsed.fragment:
                    fragment_page = page if not parsed.path else target
                    fragment_parser = page_links(fragment_page)
                    self.assertIn(parsed.fragment, fragment_parser.ids,
                                  f"broken fragment in {page.name}: {href}")

    def test_download_state_matches_evidence_gate(self):
        status = json.loads((ROOT / "evidence/submission_status.json").read_text(encoding="utf-8"))
        download_hrefs = []
        for page in DOCS.glob("*.html"):
            download_hrefs.extend(page_links(page).download_links)
        if status["status"] == "SLOT_ELIGIBLE":
            self.assertTrue(download_hrefs, "slot-eligible status requires download links")
            primary = pathlib.Path(status["primary_file"])
            fallback = pathlib.Path(status["fallback_file"])
            self.assertIn(primary.name, {urlsplit(h).path.rsplit("/", 1)[-1] for h in download_hrefs})
            for path in (ROOT / primary, ROOT / fallback):
                self.assertTrue(path.is_file(), f"linked download missing: {path}")
                receipt = path.with_name(path.stem + "-audit.json")
                self.assertTrue(receipt.is_file(), f"audit receipt missing: {receipt}")
                audit = json.loads(receipt.read_text(encoding="utf-8"))
                self.assertEqual(audit["result"], "PASS", f"audit failed: {receipt}")
                self.assertEqual(audit["ones"], 40000)
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(audit["sha256"], actual, f"receipt hash mismatch: {path.name}")
            landing = html.unescape((DOCS / "index.html").read_text(encoding="utf-8"))
            guide = html.unescape((DOCS / "executive-summary.html").read_text(encoding="utf-8"))
            for token in (status["candidate"], status["unique_submission_name"]):
                self.assertIn(token, landing, f"landing page missing {token}")
                self.assertIn(token, guide, f"guide missing {token}")
            self.assertIn(status["portal_comment"][:60], guide)
            self.assertLessEqual(len(status["portal_comment"]), 200)
            self.assertIn("UNSCRED", landing)
            self.assertIn("UNSCRED", guide)
        else:
            self.assertEqual(download_hrefs, [],
                             "a non-eligible status must not expose downloads")
            self.assertFalse(any(DOCS.glob("downloads/*.tif")),
                             "a failed candidate must not be shipped as a submission")

    def test_submission_identity_files_are_consistent(self):
        status = json.loads((ROOT / "evidence/submission_status.json").read_text(encoding="utf-8"))
        if status["status"] != "SLOT_ELIGIBLE":
            self.skipTest("no eligible submission to cross-check")
        build_receipt = next((DOCS / "downloads").glob(f"{status['candidate']}-build.json"))
        build = json.loads(build_receipt.read_text(encoding="utf-8"))
        self.assertEqual(build["arm"], status["arm"])
        self.assertTrue(build["slot_eligible_per_gate"])
        self.assertEqual(build["live_status"], "UNSCRED")
        self.assertEqual(build["files"]["nan"]["name"], pathlib.Path(status["primary_file"]).name)
        self.assertEqual(build["files"]["zeros"]["name"], pathlib.Path(status["fallback_file"]).name)
        for entry in build["novelty"]:
            self.assertLess(entry["jaccard"], 0.80)
            self.assertLess(entry["overlap_coefficient"], 0.90)
            self.assertFalse(entry["same_sha256"])


if __name__ == "__main__":
    unittest.main()
