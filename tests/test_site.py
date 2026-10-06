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
        pages = sorted(DOCS.rglob("*.html"))
        self.assertGreater(len(pages), 6, "expected merged multi-page site")
        for page in pages:
            parser = page_links(page)
            for href in parser.hrefs:
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = (page.parent / unquote(parsed.path)).resolve()
                self.assertTrue(target.is_relative_to(DOCS.resolve()),
                                f"site link escapes docs: {page.name} -> {href}")
                self.assertTrue(target.exists(), f"broken local link in {page.name}: {href}")
                if parsed.fragment:
                    fragment_page = page if not parsed.path else target
                    fragment_parser = page_links(fragment_page)
                    self.assertIn(parsed.fragment, fragment_parser.ids,
                                  f"broken fragment in {page.name}: {href}")

    def test_two_file_decision_state_matches_evidence(self):
        status = json.loads((ROOT / "evidence/submission_status.json").read_text(encoding="utf-8"))
        primary = status["primary_release"]
        self.assertEqual(primary["status"], "SLOT_ELIGIBLE")
        self.assertEqual(primary["live_status"], "UNSCRED")
        mclp = status["superseded_by"]
        self.assertEqual(mclp["status"], "GO_WITH_CAVEAT")
        self.assertIn("measurement_caveat", mclp)

        # Both shipped files exist with PASS audits whose hashes match the bytes.
        shipped = {
            pathlib.Path(primary["primary_file"]).name,
            pathlib.Path(primary["fallback_file"]).name,
            pathlib.Path(mclp["release"]["file"]).name,
        }
        download_hrefs = []
        for page in DOCS.glob("*.html"):
            download_hrefs.extend(page_links(page).download_links)
        linked = {urlsplit(h).path.rsplit("/", 1)[-1] for h in download_hrefs}
        for name in shipped:
            self.assertIn(name, linked, f"shipped file not linked for download: {name}")
        for name in (pathlib.Path(primary["primary_file"]).name,
                     pathlib.Path(primary["fallback_file"]).name):
            path = DOCS / "downloads" / name
            receipt = path.with_name(path.stem + "-audit.json")
            self.assertTrue(receipt.is_file(), f"audit receipt missing: {receipt}")
            audit = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(audit["result"], "PASS", f"audit failed: {receipt}")
            self.assertEqual(audit["ones"], 40000)
            self.assertEqual(audit["sha256"], hashlib.sha256(path.read_bytes()).hexdigest(),
                             f"receipt hash mismatch: {name}")

        # Landing page and guide carry the decision state.
        landing = html.unescape((DOCS / "index.html").read_text(encoding="utf-8"))
        guide = html.unescape((DOCS / "executive-summary.html").read_text(encoding="utf-8"))
        for token in (primary["candidate"], primary["unique_submission_name"],
                      mclp["release"]["unique_submission_name"],
                      pathlib.Path(mclp["release"]["file"]).name):
            self.assertIn(token, landing, f"landing page missing {token}")
        for token in (primary["unique_submission_name"],
                      mclp["release"]["unique_submission_name"]):
            self.assertIn(token, guide, f"guide missing {token}")
        self.assertIn(primary["portal_comment"][:60], guide)
        self.assertLessEqual(len(primary["portal_comment"]), 200)
        self.assertIn("UNSCRED", landing)
        self.assertIn("UNSCRED", guide)
        self.assertNotIn("No eligible submission download", landing)

    def test_gate_evidence_is_internally_consistent(self):
        status = json.loads((ROOT / "evidence/submission_status.json").read_text(encoding="utf-8"))
        # SUP01 primary claim reproduces from the round-2 receipt.
        claim = status["primary_release"]["equal_mass_result"]
        receipt = json.loads((ROOT / "evidence/holdout_g43_mclp.json").read_text(encoding="utf-8"))
        summary = receipt["summary"]
        d_arm = "D_SUP01_HGB|sep4.0|N40000"
        ref_arm = "REF_SH_basin_strong|sep4.0|N40000"
        self.assertAlmostEqual(summary[d_arm]["mean_dti"], claim["mean_dti"], places=6)
        self.assertAlmostEqual(summary[ref_arm]["mean_dti"], claim["reference_mean_dti"], places=6)
        self.assertAlmostEqual(summary[d_arm]["min_dti"], claim["min_fold_dti"], places=6)
        self.assertAlmostEqual(summary[d_arm]["max_dti"], claim["max_fold_dti"], places=6)
        wins = sum(1 for f in receipt["folds"]
                   if f["arms"][d_arm]["dti"] > f["arms"][ref_arm]["dti"])
        self.assertEqual(wins, claim["fold_wins_vs_reproduced_h42"])
        self.assertTrue(receipt["gate"][d_arm]["passes_holdout_promotion_gate"])
        # MCLP-line prior claim reproduces from the EXT grid receipt.
        xclaim = status["superseded_by"]["equal_mass_result"]
        xreceipt = json.loads((ROOT / "evidence/holdout_g43_cg01.json").read_text(encoding="utf-8"))
        summary = xreceipt["summary"]
        for arm, stated in ((xclaim["arm"], xclaim["mean_dti"]),
                            (xclaim["reference_arm"], xclaim["reference_mean_dti"])):
            self.assertAlmostEqual(summary[arm]["mean_dti"], stated, places=6, msg=arm)
        xwins = sum(1 for f in xreceipt["folds"]
                    if f["arms"][xclaim["arm"]]["dti"] > f["arms"][xclaim["reference_arm"]]["dti"])
        self.assertEqual(xwins, xclaim["fold_wins_vs_reproduced_h42"])
        # Round-1 CG01 bytes preserved verbatim under their own receipt.
        r1 = json.loads((ROOT / "evidence/holdout_g43_cg01_round1.json").read_text(encoding="utf-8"))
        self.assertAlmostEqual(r1["summary"]["G43-CG01_crossgradient|sep4.0|N40000"]["mean_dti"],
                               0.211567, places=6)

    def test_merge_cross_audit_marks_layouts_distinct(self):
        cross = json.loads((ROOT / "evidence/merge_cross_audit.json").read_text(encoding="utf-8"))
        pw = cross["pairwise_layout_novelty"]
        self.assertLess(pw["jaccard"], 0.80)
        self.assertLess(pw["overlap_of_sup01"], 0.90)
        self.assertLess(pw["overlap_of_mclp"], 0.90)
        for twin in ("zeros", "nan"):
            self.assertEqual(cross["mclp_file_format_via_sup01_auditor"][twin]["result"], "PASS")
        self.assertTrue(cross["mclp_file_format_via_sup01_auditor"]["sha_matches_main_claim"])


if __name__ == "__main__":
    unittest.main()
