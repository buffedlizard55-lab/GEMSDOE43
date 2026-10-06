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

    def test_download_is_offered_only_when_the_gate_has_been_passed(self):
        """The invariant the site must uphold is *not* "there is never a download" -- it is
        "a download is offered only if the preregistered promotion gate is recorded as passed".

        The original form of this test asserted a NO_GO outcome for candidate G43-CG01
        (mean 0.2116 vs the reproduced H42 reference 0.2507, 0/4 fold wins). A later arm,
        maximal covering on the supervised out-of-fold prior, was scored on the *same*
        preregistered protocol at equal mass and beat that reference 4/4 folds
        (0.286388 vs 0.250744; fold minimum 0.275090 vs the reference fold maximum 0.258025).
        Both records are in evidence/submission_status.json, and the gate decision is therefore
        read from that file rather than hard-coded either way.
        """
        status = json.loads((ROOT / "evidence" / "submission_status.json").read_text(encoding="utf-8"))
        decision = status.get("superseded_by", status)
        gate_passed = bool(decision.get("equal_mass_result", {}).get("holdout_gate_passed"))
        landing = (DOCS / "index.html").read_text(encoding="utf-8")
        shipped = sorted(DOCS.glob("downloads/*.tif"))

        if gate_passed:
            self.assertTrue(shipped, "gate passed but no submission raster was shipped")
            self.assertNotIn("No eligible submission download", landing)
        else:
            self.assertFalse(shipped, "a failed candidate must not be shipped as a submission")
            self.assertIn("No eligible submission download", landing)
            for page in DOCS.glob("*.html"):
                parser = LinkCollector()
                parser.feed(page.read_text(encoding="utf-8"))
                self.assertEqual(parser.download_links, [],
                                 f"download attribute must not expose a failed candidate: {page.name}")

    def test_gate_evidence_is_internally_consistent(self):
        """The equal-mass gate result must be reproducible from the holdout receipt itself."""
        status = json.loads((ROOT / "evidence" / "submission_status.json").read_text(encoding="utf-8"))
        claim = status.get("superseded_by", {}).get("equal_mass_result")
        self.assertIsNotNone(claim, "no equal-mass gate result recorded")
        receipt = json.loads((ROOT / "evidence" / "holdout_g43_cg01.json").read_text(encoding="utf-8"))
        summary = receipt["summary"]
        for arm, stated in ((claim["arm"], claim["mean_dti"]),
                            (claim["reference_arm"], claim["reference_mean_dti"])):
            self.assertAlmostEqual(summary[arm]["mean_dti"], stated, places=6, msg=arm)
        wins = sum(
            1 for f in receipt["folds"]
            if f["arms"][claim["arm"]]["dti"] > f["arms"][claim["reference_arm"]]["dti"])
        self.assertEqual(wins, claim["fold_wins_vs_reproduced_h42"])
        self.assertTrue(claim["holdout_gate_passed"] == (wins >= 3))


if __name__ == "__main__":
    unittest.main()
