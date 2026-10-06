#!/usr/bin/env python3
"""Render the generated part of the GitHub Pages site from the measured evidence.

MERGE NOTE (2026-10-06, PR #3 + PR #4): the six charter-required pages
(index, executive-summary, hypotheses, research, leaderboard, sources) plus
mclp-line.html are now hand-maintained merged versions covering BOTH release
lines, and ``docs/assets/site.css`` is the hand-kept light theme (the generated
pages below are inline-styled and do not use it).  This script MUST NOT
overwrite those files.  It still regenerates the MCLP-line irregularities page,
the research-note HTML, and the ``docs/data/*`` feeds.  Every number emitted
comes from ``evidence/*.json``, ``registry/*.json`` or ``docs/score-ledger.csv``.
Anything not measured is labelled as such.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from gems43 import paths, site

DOCS = paths.docs_dir()
(DOCS / "assets").mkdir(parents=True, exist_ok=True)
(DOCS / "data").mkdir(parents=True, exist_ok=True)
(DOCS / "downloads").mkdir(parents=True, exist_ok=True)
(DOCS / "research").mkdir(parents=True, exist_ok=True)

import os
TAG = os.environ.get("PIPELINE_TAG", "probe")          # evidence/pipeline_<TAG>.json
sub = site._load("submission.json")
pipe = site._load(f"pipeline_{TAG}.json")
cal = site._load("instrument_calibration.json")
chan = site._load_registry("channels.json")
man = site._load_registry("data_manifest.json")

LEADERBOARD = [
    ("#1", "alexoktaba", 0.3345), ("#2", "nchuzhoy", 0.3262),
    ("#3", "kinghorton42", 0.3222), ("#4", "Batik Shirt Brothers", 0.3218),
    ("#5", "DARD", 0.3195), ("#6", "joeyfezster", 0.3163),
    ("#7", "xiaofanhu", 0.3060), ("#8", "ndavis7", 0.2888),
    ("#9", "mzoorob", 0.2884), ("#10", "GrigorSargsyan", 0.2876),
]

IRREG = [
    ("IR-43-001", "wn", "Brief is stale on the leader",
     "The brief states \"0.3195 is the highest score right now\". On the leaderboard read "
     "2026-10-06, 0.3195 is <b>rank 5</b>; the leader is alexoktaba at 0.3345, and four teams "
     "are above 0.3195. The target used by this repository is 0.3345, not 0.3195.",
     '<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a>'),
    ("IR-43-002", "wn", "No DrivenData authentication",
     "The official data page redirects to login, so <code>training_features.tif</code>, "
     "<code>labels.tif</code> and <code>sample_submission.tif</code> cannot be downloaded from "
     "the organizer. All 23 inputs used here are owner-maintained public GitHub mirrors, "
     "accepted only because each is pinned by sha256 and byte count in "
     "<code>registry/data_manifest.json</code> and re-verified on every fetch. Every fact "
     "derived from them is labelled <span class=\"tag\">MIRROR, hash-pinned</span> rather than "
     "<span class=\"tag\">OFFICIAL</span>.",
     '<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">data page</a>'),
    ("IR-43-003", "wn", "Outbound network restricted",
     "<code>curl</code> to drivendata.org, usgs.gov, openei.org, docs.nlr.gov, "
     "earthquake.usgs.gov, raw.githubusercontent.com and sciencebase.gov all return HTTP 000 "
     "from this sandbox. Official pages quoted here were read through the browsing path; hosts "
     "reachable only by curl (the rules PDF, the USGS FDSN catalogue) are recorded as "
     "<span class=\"tag\">UNVERIFIED</span> or <span class=\"tag\">BLOCKED</span>, never assumed.",
     "measured in-sandbox, 2026-10-06"),
    ("IR-43-004", "wn", "Owner-reported scores are not organizer receipts",
     "Every live score in <code>docs/score-ledger.csv</code> — including the group best 0.2778 — "
     "is owner-reported. No submission receipt, submission ID, or hash-to-score crosswalk links "
     "any of them to a file. The 0.2778 attribution in the brief is therefore treated as "
     "<span class=\"tag\">OWNER-REPORT</span>, and no leaderboard row is attributed to a file.",
     '<a href="https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html">GEMSDOE32</a>'),
    ("IR-43-005", "no", "At n = 8 no frame is a statistically significant ranker",
     "Calibrated against every prior artifact that carries a known live score, de-duplicated by "
     "layout (n = 8 distinct submissions): frame A ρ = +0.18 (p = 0.67), frame B ρ = +0.46 "
     "(p = 0.26), frame C ρ = +0.18 (p = 0.67). <b>None reaches significance.</b> The parent "
     "project reported ρ ≈ +0.51 (n = 12, p ≈ 0.09), which is the same effect size seen through "
     "a larger sample. Read accordingly: these are <i>screens</i> that sort candidates, not "
     "evidence that a candidate will gain on the board. No promotion decision here is described "
     "as a leaderboard gain. An earlier run of this calibration counted duplicate copies of the "
     "same file (n = 31, B ρ = +0.67, p = 4e-5) — those numbers were an artifact of double "
     "counting and are not quoted anywhere.",
     "measured here, <code>evidence/instrument_calibration.json</code>"),
    ("IR-43-006", "wn", "A global Hough transform on the spring pattern is statistically invalid",
     "With 72 orientation bins and ~2,000 hot springs there are ~3×10⁶ chance collinear triples "
     "— far more than real ones. H43-3 therefore uses a locality-constrained (25 px) PCA "
     "lineament fit instead. Recorded because the obvious implementation is the wrong one.",
     "<code>docs/research/h43-hypotheses.md</code> §1 H43-3"),
    ("IR-43-007", "ok", "Disjoint-credit reduction is a hypothesis, not a bound",
     "<code>T/(0.2K + 0.8|G|)</code> equals the true index only when each dot is credited against "
     "a distinct truth pixel. When several dots compete for the same truth pixel the reduction is "
     "<b>pessimistic</b>; when there are fewer dots than truth pixels it is <b>optimistic</b>. "
     "Reported everywhere as the <i>reduction</i>, never as a bound or a guaranteed score.",
     "<code>src/gems43/metric.py</code>, <code>tests/test_metric.py</code>"),
    ("IR-43-008", "wn", "SGMC off-catalogue truth is unevenly distributed",
     "Frame B block 2 contains only 3,854 truth pixels against 31,160 in block 0, because the "
     "SGMC-derived compilation is sparse in that quadrant. Fold B2 is noisier and is reported "
     "individually rather than only pooled.",
     f"<code>evidence/pipeline_{TAG}.json</code>"),
    ("IR-43-009", "wn", "One ledger score is unsourced",
     "The brief's score table lists GEMSDOE19 <code>h19-4-multiline-…</code> at 0.1894, but the "
     "owner ledger in the previous session recorded H19-4 and H19-5 together at <b>0.1922</b>, "
     "and no submission receipt distinguishes them. The 0.1894 value is carried in "
     "<code>docs/score-ledger.csv</code> tagged <span class=\"tag\">USER-REPORT</span> and is "
     "not used in any calibration.",
     "<code>docs/score-ledger.csv</code>"),
    ("IR-43-010", "wn", "No GEMSDOE team appears in the visible top 25",
     "The brief asserts an own-best of 0.2778. The only 0.2778 on the public board is "
     "<code>extradr19</code> at rank 13, and no GEMSDOE* team name appears in the visible top 25. "
     "The 0.2778 figure is therefore treated as an owner report about a submission whose "
     "leaderboard identity has not been established, not as a verified board position.",
     '<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">'
     "leaderboard</a>"),
    ("IR-43-011", "ok", "A permuted geotransform shipped once, and its own check passed",
     "Found in the pass-2 review. <code>TRANSFORM</code> is stored in rasterio "
     "<code>Affine</code> order <code>(a, b, c, d, e, f)</code>; passing it to "
     "<code>Affine.from_gdal</code> permutes it into a geotransform that is silently valid but "
     "puts the raster's top-left at (100, 0) with bounds reaching 1.7&times;10<sup>10</sup>. It "
     "was not caught because the check compared <code>transform.to_gdal()</code> back against "
     "<code>TRANSFORM</code> &mdash; and <code>to_gdal</code> is the <i>inverse</i> permutation, "
     "so it round-trips the error and always matches. Both are fixed, the file was rebuilt, and "
     "the check now compares the affine members and the numeric bounds against the mirrored "
     "template, asserted by "
     "<code>tests/test_submission.py::test_transform_matches_the_template</code>. Recorded "
     "because the failure mode generalises: a check that inverts the thing it is checking "
     "verifies nothing.",
     "<code>src/gems43/grid.py</code>, <code>src/gems43/submission.py</code>"),
]


# --------------------------------------------------------------------------------------
# A deliberately small Markdown -> HTML converter for the three research notes, so that the
# site's links to them resolve and the .md files stay the single source of truth.  It handles
# exactly the constructs those notes use: ATX headings, fenced code, pipe tables, bullets,
# block quotes and inline code/bold/links.  Anything else is escaped and passed through.
# --------------------------------------------------------------------------------------
def _inline(t: str) -> str:
    import re as _re

    def _link(m: "_re.Match") -> str:
        # The research .md files live at docs/research/*.md, so a relative
        # target is resolved against the repository root and pointed at the
        # rendered GitHub blob view: Pages serves docs/ as its root, where a
        # raw ../.. link would 404.  (Merge fix, 2026-10-06.)
        text, target = m.group(1), m.group(2)
        if target.startswith("../"):
            import posixpath as _pp
            repo_rel = _pp.normpath(_pp.join("docs/research", target))
            target = ("https://github.com/buffedlizard55-lab/GEMSDOE43/blob/main/" + repo_rel)
        return f'<a href="{target}">{text}</a>'

    t = site._esc(t)
    t = _re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = _re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = _re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link, t)
    return t


def md_to_html(md: str) -> str:
    import re as _re
    out, buf, in_code, in_ul, tbl = [], [], False, False, []

    def flush():
        nonlocal buf
        if buf:
            out.append("<p>" + " ".join(_inline(x) for x in buf) + "</p>")
            buf = []

    def flush_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def flush_tbl():
        nonlocal tbl
        if tbl:
            rows = [r for r in tbl if set(r.replace("|", "").strip()) != {"-"}]
            body = []
            for i, r in enumerate(rows):
                cells = [c.strip() for c in r.strip().strip("|").split("|")]
                tag = "th" if i == 0 else "td"
                body.append("<tr>" + "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells)
                            + "</tr>")
            out.append("<table>" + "".join(body) + "</table>")
            tbl = []

    for line in md.splitlines():
        if line.strip().startswith("```"):
            flush(); flush_ul(); flush_tbl()
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                out.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            out.append(site._esc(line))
            continue
        if not line.strip():
            flush(); flush_ul(); flush_tbl()
            continue
        if line.startswith("|"):
            flush(); flush_ul()
            tbl.append(line)
            continue
        flush_tbl()
        m = _re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush(); flush_ul()
            lvl = len(m.group(1))
            out.append(f'<h{lvl}>{_inline(m.group(2))}</h{lvl}>')
            continue
        if line.startswith("> "):
            flush(); flush_ul()
            out.append(f'<blockquote>{_inline(line[2:])}</blockquote>')
            continue
        m = _re.match(r"^\s*[-*]\s+(.*)$", line)
        if m:
            flush()
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_inline(m.group(1))}</li>")
            continue
        buf.append(line.strip())
    flush(); flush_ul(); flush_tbl()
    return "\n".join(out)


def render_research_pages() -> None:
    """Emit docs/research/<slug>.html for every Markdown note the site links to."""
    for src in sorted((DOCS / "research").glob("*.md")):
        title = src.stem.replace("-", " ").title()
        body = f'<div class="panel"><h2 style="margin-top:0;border:0">{site._esc(title)}</h2>' \
               f'{md_to_html(src.read_text())}</div>'
        page = site.layout(f"GEMSDOE43 — {title}", body, "research.html",
                           "Research note — source of truth is the .md in the repository",
                           prefix="../")
        (DOCS / "research" / (src.stem + ".html")).write_text(page, encoding="utf-8")
        print(f"  wrote docs/research/{src.stem}.html ({len(page):,} bytes)")


# --------------------------------------------------------------------------------------
def page_index() -> str:
    body = site.download_block(sub)
    lb = "".join(
        f'<tr><td class="n">{r}</td><td>{site._esc(t)}</td><td class="n">{s:.4f}</td></tr>'
        for r, t, s in LEADERBOARD)
    sel0 = sub.get("selection", {}) if sub else {}
    row0 = sel0.get("chosen", {}) or {}
    bar = (cal or {}).get("reference_bar", {}) or {}
    cards = ""
    if pipe and row0:
        def pct(fam):
            b = bar.get(fam, {}).get("best_scored_mean_dti")
            v = row0.get(fam)
            if not b or not v:
                return "&mdash;"
            return f"{100 * (v / b - 1):+.0f}%"
        # The headline is the *selected* surface against the reference bar set by the best
        # previously-scored artifact -- not the arg-max over the whole grid, which is won by a
        # surface whose frame-B truth is the inventory it was built from (IR-43-008).
        cards = f"""
<div class="grid">
<div class="card"><div class="v">{row0.get('A', 0):.4f}</div>
  <div class="k">frame A holdout DTI &mdash; {pct('A')} vs the best scored artifact
  ({bar.get('A', {}).get('best_scored_mean_dti', 0):.4f})</div></div>
<div class="card"><div class="v">{row0.get('C', 0):.4f}</div>
  <div class="k">frame C holdout DTI &mdash; {pct('C')} vs the best scored artifact
  ({bar.get('C', {}).get('best_scored_mean_dti', 0):.4f})</div></div>
<div class="card"><div class="v">{row0.get('B', 0):.4f}</div>
  <div class="k">frame B holdout DTI &mdash; {pct('B')} vs the best scored artifact
  ({bar.get('B', {}).get('best_scored_mean_dti', 0):.4f})</div></div>
<div class="card"><div class="v">{(1 - np.e ** -1):.4f}</div>
  <div class="k">worst-case guarantee of the greedy (1 − 1/e)</div></div>
<div class="card"><div class="v">{len(chan['channels']) if chan else 0}</div>
  <div class="k">derived geophysical channels</div></div>
<div class="card"><div class="v">23/23</div>
  <div class="k">hash-pinned inputs verified</div></div>
</div>
<p class="small">Frames A and C withhold catalogue faults by spatial block; frame B uses the
off-catalogue external inventory. The bar is the mean holdout DTI of the best artifact that has a
known live score, measured on the same frames. Frame B is <b>excluded from selection</b> because
its truth set is the SGMC inventory that several candidate surfaces are built from;
<code>lf_ext_sgmc</code> tops the raw grid at 0.1968 for exactly that reason and is not shipped.
The calibration of these frames against live scores is published with its p-value on the
<a href="irregularities.html">irregularities</a> page: at n = 8 none is significant, so these
are screens, not evidence of a leaderboard gain.</p>"""
    sel = sub.get("selection", {}) if sub else {}
    row = sel.get("chosen", {})
    body += f"""
<div class="panel">
<h2 style="margin-top:0;border:0">What this submission is</h2>
<p>The competition's <i>distance-weighted Tversky index</i> is, for a fixed number of emitted
points, <b>exactly</b> the <b>Maximal Covering Location Problem</b> of Church &amp; ReVelle
(1974): place <i>K</i> facilities of service radius 300 m to maximise the demand covered. This
repository solves that problem directly on a continuous probability surface with the submodular
greedy algorithm, which carries a proven <b>(1 − 1/e) ≈ 63.2 %</b> worst-case guarantee against
the true optimum — a formal floor that no hand-picked spacing constant has.</p>
<p>The second free parameter, the number of dots, is <b>derived rather than swept</b>. Because the
index's denominator rises by exactly <code>0.2</code> per emitted dot whatever that dot's credit,
a dot is worth emitting iff its marginal coverage exceeds <code>0.2 × DTI</code>. Solving that
condition self-consistently is a Dinkelbach fixed point, so there is no spacing constant and no
magic budget anywhere in the pipeline.</p>
{cards}
</div>

<div class="panel">
<h2 style="margin-top:0;border:0">Public leaderboard, read 2026-10-06</h2>
<table><tr><th>rank</th><th>participant</th><th class="n">best public DW-Tversky</th></tr>{lb}</table>
<p class="small">Public leaderboard only; it is not the private or final prize score.
Group best is <b>0.2778</b> (<span class="tag">OWNER-REPORT</span> GEMSDOE32 / h33-2-b2), which
today would sit just below rank 13.</p>
</div>

<div class="panel">
<h2 style="margin-top:0;border:0">Where the headroom is</h2>
<p>The group's best artifact realises <b>0.126</b> weighted credit per emitted dot against a
theoretical <b>3.0</b> for a dot sitting on a straight fault trace
(<code>1 + 2·(2/3) + 2·(1/3)</code>) — about <b>4 %</b>. The gap between 0.2778 and the top of the
board is therefore <b>not an emission-quality gap and not a spacing gap; it is a coverage gap</b>,
which is precisely what the covering formulation optimises. Full algebra in
<a href="research.html">Method</a>.</p>
</div>
"""
    return site.layout("GEMSDOE43 — maximal-covering emission for the DOE GEMS prize", body,
                       "index.html",
                       "DrivenData #306 · distance-weighted Tversky · Church–ReVelle MCLP solver")


def _gate_panel() -> str:
    """The preregistered promotion gate, measured on the repository's own four-fold protocol."""
    import json

    from gems43 import paths

    st_path = paths.evidence_dir() / "submission_status.json"
    if not st_path.exists():
        return ""
    st = json.loads(st_path.read_text())
    d = st.get("superseded_by") or st
    r = d.get("equal_mass_result") or {}
    if not r:
        return ""
    fold = d.get("equal_mass_result", {})
    wins = r.get("fold_wins_vs_reproduced_h42")
    passed = bool(r.get("holdout_gate_passed"))
    verdict = ('<span class="ok">GATE PASSED</span>' if passed
               else '<span class="no">GATE FAILED</span>')
    return f"""
<div class="panel">
<h2 style="margin-top:0;border:0">Did it clear the preregistered promotion gate?</h2>
<p>{verdict} — this repository's own four-fold protocol (200-cell blocks, 3-px edge guard,
2-px training-trace guard, official 300&nbsp;m triangular-kernel DTI), scored at
<b>equal mass 40,000</b> on the <b>same</b> allowed emission domain as the reproduced H42
baseline.</p>
<table>
<tr><th>arm</th><th class="n">mean DTI</th><th class="n">min fold</th><th class="n">max fold</th>
<th class="n">folds won</th></tr>
<tr><td><b>{site._esc(r.get('arm', ''))}</b> (this submission's prior)</td>
<td class="n">{r.get('mean_dti')}</td><td class="n">{r.get('min_fold_dti')}</td>
<td class="n">{r.get('max_fold_dti')}</td><td class="n">{wins}/{r.get('folds')}</td></tr>
<tr><td>{site._esc(r.get('reference_arm', ''))} (H42 baseline)</td>
<td class="n">{r.get('reference_mean_dti')}</td><td class="n">&mdash;</td>
<td class="n">{r.get('reference_max_fold_dti')}</td><td class="n">&mdash;</td></tr>
</table>
<p class="small"><b>Two caveats, both material.</b>
(1)&nbsp;An earlier comparison of the shipped 51,053-dot full-grid layout against the same
reference scored 0.219994 and won 0/4 folds — but it had only ~13.7k of its dots inside each
fold's allowed domain against the reference's 40,000, so that was a <b>mass artefact, not a
result</b>. The number above is the same prior packed at equal mass.
(2)&nbsp;The shipped file is emitted by the maximal-covering solver with <b>no separation
constraint</b> and a Dinkelbach-derived budget, and <i>that exact emission has not yet been
scored at equal mass on this protocol</i>. The prior is validated; the specific placement is not.
Both records are kept in <code>evidence/submission_status.json</code> — the earlier NO_GO for a
different arm (G43-CG01) is preserved rather than overwritten.
(3)&nbsp;The truth here is withheld <i>published-catalogue</i> faults, not the hidden competition
label set. This is a screen, not a score forecast.</p>
</div>"""


def _novelty_panel() -> str:
    nv = (sub or {}).get("novelty") or {}
    if nv.get("skipped"):
        return ("<p class=\"small\">The near-duplicate screen has not been run for this build "
                f"({site._esc(str(nv.get('reason', 'unknown')))}). "
                "Do not submit until it has.</p>")
    sub_k = nv.get("by_kind", {}).get("submission", {})
    inp_k = nv.get("by_kind", {}).get("input", {})
    rows = "".join(
        f'<tr><td class="n">{r["coverage_iou"]:.3f}</td>'
        f'<td class="n">{max(r["new_within_300m_of_prior"], r["prior_within_300m_of_new"]):.3f}</td>'
        f'<td class="n">{r.get("containment_excess", float("nan")):.2f}</td>'
        f'<td class="n">{r["median_nn_distance_px"]:.1f}</td>'
        f'<td class="n">{r["prior_dots"]:,}</td>'
        f'<td>{site._esc(r["artifact"])}</td>'
        f'<td>{site._esc(r.get("kind", ""))}</td></tr>'
        for r in nv.get("top", [])[:8])
    verdict = ("PASS — no prior submission is a near-duplicate"
               if not sub_k.get("dupes") else
               f'<span class="no">FAIL — {len(sub_k["dupes"])} prior submission(s) flagged</span>')
    return f"""
<p>Every earlier GEMSDOE artifact reachable from GitHub was collected
(<b>{nv.get('n_compared', 0)}</b> rasters of the right grid) and compared to this layout on four
statistics. The one that decides is the <b>coverage IoU</b>: both dot sets are dilated by the
competition's own triangular 300 m kernel and the two coverage fields are compared, i.e. "would
the scorer see these as the same prediction?".</p>
<table>
<tr><th>class</th><th class="n">n</th><th class="n">worst coverage IoU</th>
<th class="n">worst excess containment</th><th>verdict</th></tr>
<tr><td><b>submissions</b> (published predictions)</td><td class="n">{sub_k.get('n', 0)}</td>
<td class="n">{f"{sub_k['worst_iou']:.3f}" if sub_k.get('worst_iou') is not None else '&mdash;'}</td>
<td class="n">{f"{sub_k['worst_containment_excess']:.2f}" if sub_k.get('worst_containment_excess') is not None else '&mdash;'}</td>
<td>{verdict}</td></tr>
<tr><td>inputs / derived assets</td><td class="n">{inp_k.get('n', 0)}</td>
<td class="n">{f"{inp_k['worst_iou']:.3f}" if inp_k.get('worst_iou') is not None else '&mdash;'}</td>
<td class="n">{f"{inp_k['worst_containment_excess']:.2f}" if inp_k.get('worst_containment_excess') is not None else '&mdash;'}</td>
<td class="small">overlap expected — the model is trained on the catalogue and the SGMC
inventory is a superset of it; these were never submitted, so they are not duplicates</td></tr>
</table>
<h3>Closest eight artifacts in the whole corpus</h3>
<table>
<tr><th class="n">coverage IoU</th><th class="n">300 m containment</th>
<th class="n">excess over chance</th><th class="n">median NN (px)</th>
<th class="n">its dots</th><th>artifact</th><th>class</th></tr>{rows}
</table>
<p class="small"><b>Reading the containment column.</b> Raw 300 m containment is <i>not</i> the
deciding statistic and is not thresholded: with K dots of 29-cell support in N eligible cells,
two unrelated layouts already overlap by <code>1 &minus; (1 &minus; 29/N)<sup>K</sup></code>,
which is 0.25 at K = 51k and 0.63 at K = 176k &mdash; so a flat 0.60 threshold flags ordinary
unrelated priors (it flagged 26 of them here, nearly all of them input rasters). What is
thresholded at {nv.get('iou_limit', 0.5)} is the coverage IoU, together with the <b>excess over
chance</b>, <code>(observed &minus; chance)/(1 &minus; chance)</code>, at 0.60: exactly 0 for two
unrelated layouts and exactly 1 for a perfect duplicate. A one-pixel translation and a 10 %
dot jitter both score an IoU above 0.90 here, so the screen would catch a re-upload wearing a
different hash.</p>"""


def page_exec() -> str:
    name = site._esc(sub.get("portal_name", "GEMSDOE43-MCLP")) if sub else "GEMSDOE43-MCLP"
    note = site._esc(sub.get("submission_note", "")) if sub else ""
    z = (sub or {}).get("files", {}).get("zeros", {})
    nanf = (sub or {}).get("files", {}).get("nan", {})
    zipf = (sub or {}).get("files", {}).get("zip", {})
    href = f"downloads/{z.get('filename', 'submission.tif')}"
    zname = site._esc(z.get("filename", "submission.tif"))
    zsize = f"{z.get('size_bytes', 0) / 1e6:.2f}"
    nname = site._esc(nanf.get("filename", ""))
    zs = site._esc(z.get("sha256", ""))[:32]
    nov = _novelty_panel()
    gate = _gate_panel()
    body = f"""
<div class="panel hero">
<h2 style="margin-top:0;border:0">How to submit — four steps</h2>
<div class="step"><b>1. Download the file.</b>
<a class="btn" href="{href}">&#11015; Download {zname}</a>
<a class="btn alt" href="downloads/{nname}">NaN-outside twin</a>
<a class="btn alt" href="downloads/{site._esc(zipf.get('filename', ''))}">.zip</a><br>
<b>Upload the <code>-zeros.tif</code> file.</b> Single-band float32 GeoTIFF, EPSG:32611, 100 m,
3730 × 3292, {zsize} MB, every one of the 12,279,160 cells finite and inside [0,&nbsp;1].
Portal name to use: <code>{name}</code>.<br>
<span class="small">sha256 (first 32 hex) <code>{zs}</code> · in-footprint values of the three
files are bit-identical; they differ only in how the cells outside the scoring footprint are
written.</span></div>
<div class="step"><b>2. Open the DrivenData submission form.</b>
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">drivendata.org/competitions/306/…/submissions/</a>
→ <i>New submission</i> → <i>File to submit</i> → choose the <code>.tif</code> (or the
<code>.zip</code>).</div>
<div class="step"><b>3. Paste the note below into the “Note (optional)” field.</b>
This is what makes the row identifiable later.
<pre>{note}</pre></div>
<div class="step"><b>4. Submit.</b> The portal will accept the file: it cannot fail the
<i>“Predicted values must be in range [0, 1]”</i> check, because every cell is finite and in
[0,&nbsp;1] — verified by an independent re-read of the written bytes, not by the writer.</div>
</div>

{gate}

<div class="panel">
<h2 style="margin-top:0;border:0">Uniqueness — is this the same answer as an earlier upload?</h2>
{nov}
</div>

<div class="panel">
<h2 style="margin-top:0;border:0">Why an earlier upload was rejected with
“Predicted values must be in range [0, 1]”</h2>
<p>Two mechanisms in the competition's own inputs produce that condition, and both were measured:
(<b>a</b>) <code>training_features.tif</code> declares its nodata as
<code>-3.4028234663852886e+38</code> and contains <b>3,061 sentinel cells per band inside the
scoring footprint</b> — a pipeline that reads the bands without replacing the sentinel ships cells
worth −3.4×10³⁸; (<b>b</b>) the feature bands' valid region is <b>smaller</b> than the
submission template's, so a footprint mask taken from a feature band strands scored cells as NaN,
and NaN fails any <code>((v &gt;= 0) &amp; (v &lt;= 1)).all()</code> check.</p>
<p>The writer used here repairs the sentinel before any transform, derives the footprint from
<code>sample_submission.tif</code> (the organizer's own template), and then <b>fails closed</b>:
it re-reads the written file and aborts if any cell is non-finite, out of range, or if the grid
drifted. Details: <a href="research/range-error-root-cause.html">root-cause note</a> (inherited
from GEMSDOE30/32, re-verified here).</p>
</div>

<div class="panel">
<h2 style="margin-top:0;border:0">Which outside-encoding to use</h2>
<table>
<tr><th>encoding</th><th>outside the footprint</th><th>why</th></tr>
<tr><td><b><code>-zeros.tif</code> (recommended)</b></td><td>0.0</td>
<td>What the organizer's own reference solution emits — <code>rasterio.open(…, count=1, dtype=…)</code>
with <b>no</b> <code>nodata</code> argument on a finite array. The owner ledger shows the two
encodings scoring identically (<code>r7-nms3-dem10-scarp_0c9199f14e62</code> = 0.1294 and
<code>…_allfinite</code> = 0.1294). It can never trip a whole-raster range check.</td></tr>
<tr><td><code>-nan.tif</code></td><td>NaN</td>
<td>The literal wording of the specification (“data outside the bounds is null or nan”).
Bit-identical in-footprint values to the zeros file.</td></tr>
</table>
</div>
"""
    return site.layout("Executive summary — how to make the submission", body,
                       "executive-summary.html", "Four steps, one file, one note to paste.")


def page_hyp() -> str:
    rows = ""
    if pipe:
        tab = []
        for s, e in pipe["surfaces"].items():
            for k, v in e["frames"].items():
                tab.append((s, int(k),
                            v.get("pooled_A", {}).get("mean_dti", 0.0),
                            v.get("pooled_B", {}).get("mean_dti", 0.0),
                            v.get("pooled_C", {}).get("mean_dti", 0.0),
                            v.get("pooled_all", {}).get("mean_dti", 0.0),
                            int(e["emission_plan"]["k_star"])))
        tab.sort(key=lambda r: -r[5])
        for r in tab[:40]:
            rows += (f'<tr><td>{site._esc(r[0])}</td><td class="n">{r[1]:,}</td>'
                     f'<td class="n">{r[2]:.4f}</td><td class="n">{r[3]:.4f}</td>'
                     f'<td class="n">{r[4]:.4f}</td><td class="n"><b>{r[5]:.4f}</b></td>'
                     f'<td class="n">{r[6]:,}</td></tr>')
    corr = ""
    if cal and cal.get("correlations"):
        for fam, c in cal["correlations"].items():
            if c:
                corr += (f'<tr><td>{fam}</td><td class="n">{c["n"]}</td>'
                         f'<td class="n">{c["spearman_rho"]:+.3f}</td>'
                         f'<td class="n">{c["p_value"]:.3f}</td></tr>')
            else:
                corr += f'<tr><td>{fam}</td><td class="n">—</td><td colspan="2">not measured</td></tr>'
    bar = ""
    if cal and cal.get("reference_bar"):
        for fam, b in cal["reference_bar"].items():
            bar += (f'<tr><td>{fam}</td><td>{site._esc(b["best_scored_artifact"])}</td>'
                    f'<td class="n">{b["best_scored_live"]:.4f}</td>'
                    f'<td class="n">{b["best_scored_mean_dti"]:.4f}</td></tr>')
    body = f"""
<div class="panel">
<h2 style="margin-top:0;border:0">The five candidates</h2>
<p>Full write-up with layers, physical signature, off-catalogue mechanism, novelty and cost:
<a href="research/h43-hypotheses.html">H43 hypotheses</a> (also
<code>docs/research/h43-hypotheses.md</code> in the repository). Summary:</p>
<table>
<tr><th>#</th><th>hypothesis</th><th>layers</th><th>signature</th><th>status</th></tr>
<tr><td class="n">1</td><td>Magnetic source-edge lineaments</td>
<td><code>tc</code>, <code>tmi_hg</code>, <code>tmi_vg</code>, <code>tmi</code>, <code>rtp</code></td>
<td>analytic signal + tilt-angle edge/zero-band + Frangi line response</td>
<td class="ok">built, measured</td></tr>
<tr><td class="n">2</td><td>Concealed basin-bounding faults</td>
<td><code>depth_to_base_surf</code>, <code>cond_surf</code>, <code>geod_shearrate</code></td>
<td>3-way coincidence × <b>concealment gate</b></td><td class="ok">built, measured</td></tr>
<tr><td class="n">3</td><td>Geothermal-fluid conduit alignment</td>
<td>GDR thermal springs + volcanic vents</td>
<td>locality-constrained PCA lineament through the point pattern</td>
<td class="ok">built, measured</td></tr>
<tr><td class="n">4</td><td>Gravity source-parameter imaging</td>
<td>4 <code>iso_grav_anom*</code> bands</td>
<td>tilt-depth SPI + gravity analytic signal</td><td class="ok">built, measured</td></tr>
<tr><td class="n">5</td><td>Sub-km seismicity lineaments</td>
<td>raw USGS FDSN catalogue</td><td>epicentres + nodal-plane strikes</td>
<td class="no"><b>BLOCKED</b> — host unreachable here</td></tr>
</table>
</div>

<div class="panel">
<h2 style="margin-top:0;border:0">Is the instrument any good? (the question that has to come first)</h2>
<p>Spearman rank correlation of each frame family against the owner-reported live scores, over the
artifacts whose live score is already known:</p>
<table><tr><th>frame family</th><th class="n">n</th><th class="n">ρ</th>
<th class="n">p</th></tr>{corr or '<tr><td colspan="4">not measured yet</td></tr>'}</table>
<p><b>Reference bar</b> — the best mean DTI achieved on each family by an artifact that has a known
live score. A candidate must clear this before it is promoted:</p>
<table><tr><th>family</th><th>artifact</th><th class="n">its live score</th>
<th class="n">its mean DTI on this family</th></tr>
{bar or '<tr><td colspan="4">not measured yet</td></tr>'}</table>
<p class="small">The parent project measured ρ ≈ +0.51 (n = 12, p ≈ 0.09) for its catalogue
instrument. A correlation of that size is a <b>screen</b>, not evidence of a leaderboard gain,
and no submission is described here as a predicted score.</p>
</div>

<div class="panel">
<h2 style="margin-top:0;border:0">Measured results — every surface × every budget</h2>
<p>Pooled mean DW-Tversky over the four spatial blocks of each family. <b>A</b> = catalogue
components held out by block; <b>B</b> = SGMC faults the catalogue does not contain;
<b>C</b> = catalogue components with a 300 m flank deleted. Top 40 rows of
{len(pipe['surfaces']) if pipe else 0} surfaces × budgets.</p>
<table><tr><th>surface</th><th class="n">K</th><th class="n">A</th><th class="n">B</th>
<th class="n">C</th><th class="n">pooled</th><th class="n">K* (marginal rule)</th></tr>{rows}</table>
</div>
"""
    return site.layout("Hypotheses and validation", body, "hypotheses.html",
                       "Five untried geological hypotheses, ranked, then measured.")


def page_research() -> str:
    chrows = ""
    if chan:
        for c in chan["channels"]:
            chrows += (f'<tr><td class="n">{c["index"]}</td><td><code>{site._esc(c["name"])}</code></td>'
                       f'<td>{site._esc(c["hypothesis"])}</td>'
                       f'<td class="small">{site._esc(c["note"])}</td></tr>')
    body = f"""
<div class="panel">
<h2 style="margin-top:0;border:0">The metric, verbatim</h2>
<p>From <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">the
official problem description</a>, “Performance metric”, read 2026-10-06:</p>
<pre>k(d)  = max(1 - d/R, 0),                       R = 300 m
TP_w  = sum_{{g in G}} max_{{x: d(x,g) &lt;= R}} p(x) k(d(x,g))
FP_w  = sum_{{x: p(x) &gt; 0}} p(x) [1 - max_{{g in G}} k(d(x,g))]
FN_w  = sum_{{g in G}} [1 - max_{{x: d(x,g) &lt;= R}} p(x) k(d(x,g))]
DTI   = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w + eps)</pre>
<p>Implemented verbatim in <code>src/gems43/metric.py</code>, and tested against
(<b>i</b>) the organizer's own worked example
<code>TP_w=3.00, FP_w=1.89, FN_w=2.00 → 0.60</code> and (<b>ii</b>) a brute-force
<code>O(N·M)</code> re-derivation on random grids.</p>
</div>

<div class="panel">
<h2 style="margin-top:0;border:0">Three consequences, and what each one buys</h2>
<table>
<tr><th>#</th><th>consequence</th><th>consequence for the design</th></tr>
<tr><td class="n">1</td><td><code>FN_w = |G| − TP_w</code>, so
<code>DTI = T / (0.2T + 0.2F + 0.8|G|)</code></td>
<td>the index is a ratio of two set functions → fractional-programming tools apply</td></tr>
<tr><td class="n">2</td><td>Adding a pixel of weight <code>p</code> raises the denominator by
<b>exactly <code>0.2p</code></b> whatever its credit, so the move pays iff
<code>k &gt; 0.2·DTI</code> — <b>independent of <code>p</code></b></td>
<td><b>binary emission is optimal</b>; the stopping rule needs no tuned threshold</td></tr>
<tr><td class="n">3</td><td><code>FP_w = |S| − Σ_i k_i</code> is <b>modular</b> in the emitted
set; under the disjoint-credit hypothesis the index reduces to
<code>T / (0.2|S| + 0.8|G|)</code></td>
<td>for a fixed dot count, the problem <b>is</b> MCLP</td></tr>
</table>
<p class="small"><b>Correction recorded as IR-43-007:</b> the reduction in row 3 is a
<i>hypothesis</i>, not a bound. It is pessimistic when several dots compete for the same truth
pixel (the regime at K &gt; |G|) and optimistic when there are fewer dots than truth pixels.
It is reported as the <i>reduction</i> everywhere, never as a guaranteed score.</p>
</div>

<div class="panel">
<h2 style="margin-top:0;border:0">From MCLP to the emitted file</h2>
<ol>
<li><b>Demand field.</b> A per-pixel prior <code>π(x)</code> that a hidden fault occupies
<code>x</code>, normalised so <code>Σ π = |Ĝ|</code> (12,226, the parent project's live-anchor
estimate). That normalisation is what puts the marginal gains on the metric's own scale.</li>
<li><b>Coverage objective.</b> <code>T(S) = Σ_x π(x)·max_{{i∈S}} k(d(i,x))</code> — weighted
max-coverage, hence <b>monotone submodular</b>.</li>
<li><b>Church–ReVelle greedy with exact residual bookkeeping.</b> Unlike a textbook MCLP, coverage
is a <i>graded</i> kernel, so the solver tracks <code>max(0, k(δ) − C(x))</code> at every pixel and
two overlapping facilities are credited only once. It is the <b>exact</b> greedy (not lazy): after
each acceptance only the candidates within 600 m can have changed, so a full pass per iteration is
unnecessary. Worst-case guarantee <b>(1 − 1/e) = 0.6321</b>.</li>
<li><b>Cardinality by Dinkelbach fixed point.</b> One greedy pass produces the whole marginal-gain
path; the budget is where the marginal gain falls below <code>0.2·s</code>, solved
self-consistently. <b>No spacing constant, no swept budget.</b></li>
<li><b>Binary emission</b> (<code>p = 1</code> on the chosen dots), because consequence 2 makes
<code>p &lt; 1</code> strictly dominated.</li>
<li><b>Fail-closed write</b>, then an independent re-read audit, then the near-duplicate screen.</li>
</ol>
</div>

<div class="panel">
<h2 style="margin-top:0;border:0">Channel provenance ({len(chan['channels']) if chan else 0} channels)</h2>
<p>Every channel names the band and the transform it came from. Band names are read from the
GeoTIFF's own descriptions, never assumed.</p>
<table><tr><th class="n">#</th><th>channel</th><th>hypothesis</th><th>what it is</th></tr>{chrows}</table>
</div>
"""
    return site.layout("Method — metric algebra, MCLP, and the channel stack", body,
                       "research.html", "Every step proved, every constant derived.")


def page_leaderboard() -> str:
    lb = "".join(
        f'<tr><td class="n">{r}</td><td>{site._esc(t)}</td><td class="n">{s:.4f}</td></tr>'
        for r, t, s in LEADERBOARD)
    led = ""
    p = DOCS / "score-ledger.csv"
    if p.exists():
        with p.open() as fh:
            for row in csv.DictReader(fh):
                led += (f"<tr><td>{site._esc(row.get('site',''))}</td>"
                        f"<td class=\"small\">{site._esc(row.get('submission',''))}</td>"
                        f"<td class=\"n\">{site._esc(row.get('score',''))}</td>"
                        f"<td class=\"small\">{site._esc(row.get('evidence_class',''))}</td></tr>")
    body = f"""
<div class="panel">
<h2 style="margin-top:0;border:0">Public leaderboard — read 2026-10-06</h2>
<table><tr><th>rank</th><th>participant</th><th class="n">best public DW-Tversky</th></tr>{lb}</table>
<p class="small">Source:
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">official
leaderboard</a>. Public score only — it is not the private or final prize score. The page is
dynamic; this is a dated snapshot, not a live feed.</p>
</div>
<div class="panel">
<h2 style="margin-top:0;border:0">Group submission ledger</h2>
<p>Every row is <span class="tag">OWNER-REPORT</span> unless the evidence class says otherwise.
No row is linked to a file by an organizer receipt.</p>
<table><tr><th>site</th><th>submission</th><th class="n">score</th><th>class</th></tr>{led}</table>
</div>
"""
    return site.layout("Scores, leaderboard and ledger", body, "leaderboard.html",
                       "Dated snapshots; no score is attributed to a file without a receipt.")


def page_sources() -> str:
    rows = ""
    if man:
        for f in man["files"]:
            rows += (f'<tr><td class="small">{site._esc(f["id"])}</td>'
                     f'<td class="n">{f["bytes"]:,}</td>'
                     f'<td class="small"><code>{site._esc(f["sha256"][:32])}…</code></td>'
                     f'<td class="small">{site._esc(f.get("repo",""))}@{site._esc(str(f.get("ref",""))[:12])}</td></tr>')
    body = f"""
<div class="panel">
<h2 style="margin-top:0;border:0">Official sources</h2>
<table><tr><th>fact</th><th>source</th></tr>
<tr><td>Metric, submission format, prize structure</td>
<td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">page 967</a>
— read 2026-10-06</td></tr>
<tr><td>Public leaderboard</td>
<td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a>
— read 2026-10-06</td></tr>
<tr><td>Known USGS/INGENIOUS faults are masked from scoring</td>
<td>DrivenData staff <code>chrisk-dd</code>,
<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">forum thread 11516</a></td></tr>
<tr><td>Official rules PDF</td>
<td><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">docs.nlr.gov/docs/fy26osti/96647.pdf</a>
— <span class="wn">host unreachable from this sandbox; URL recorded, contents UNVERIFIED</span></td></tr>
<tr><td>Reference solution (writes an all-finite, nodata-free raster)</td>
<td><a href="https://github.com/drivendataorg/gems-prize-reference-solution">drivendataorg/gems-prize-reference-solution</a></td></tr>
<tr><td>GeoDAWN survey — the study area</td>
<td><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS data page</a>;
<a href="https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7">ScienceBase item</a></td></tr>
<tr><td>INGENIOUS / GDR submission 1391 (spring, well, vent, paleo-geothermal data; CC BY 4.0)</td>
<td><a href="https://gdr.openei.org/submissions/1391">gdr.openei.org/submissions/1391</a>;
<a href="https://gbcge.org/current-projects/ingenious/">Great Basin Center for Geothermal Energy</a></td></tr>
<tr><td>Church &amp; ReVelle (1974), maximal covering location problem</td>
<td><a href="https://link.springer.com/article/10.1007/BF01942293">Papers of the Regional Science Association 32: 101–118</a></td></tr>
<tr><td>Analytic signal for contact mapping</td>
<td>Nabighian (1972) <i>Geophysics</i> 37(6); Roest, Verhoef &amp; Pilkington (1992) <i>Geophysics</i> 57(1)</td></tr>
<tr><td>Tilt angle / tilt-depth (SPI)</td>
<td>Miller &amp; Singh (1994) <i>Geophysics</i>; Salem et al. (2007) <i>Geophysics</i> 72(2)</td></tr>
<tr><td>Frangi vesselness</td><td>Frangi et al. (1998) <i>IEEE TMI</i> 17(4)</td></tr>
<tr><td>Submodular greedy guarantee</td>
<td>Nemhauser, Wolsey &amp; Fisher (1978) <i>Mathematical Programming</i> 14</td></tr>
</table>
</div>

<div class="panel">
<h2 style="margin-top:0;border:0">Inputs — every byte pinned and re-verified</h2>
<p class="small">The DrivenData data page requires a login this environment does not have. All 23
inputs below are owner-maintained public GitHub mirrors, accepted <b>only</b> because each is
pinned by sha256 and byte count in <code>registry/data_manifest.json</code> and re-verified by
<code>scripts/fetch_mirrors.sh</code> on every fetch (it exits non-zero on any mismatch). They are
labelled <span class="tag">MIRROR, hash-pinned</span>, never <span class="tag">OFFICIAL</span>.</p>
<table><tr><th>id</th><th class="n">bytes</th><th>sha256</th><th>source</th></tr>{rows}</table>
</div>
"""
    return site.layout("Sources", body, "sources.html", "Official first, mirrors pinned and labelled.")


def page_irreg() -> str:
    rows = "".join(
        f'<tr><td><code>{i}</code></td><td class="{cls}">●</td>'
        f'<td><b>{t}</b></td><td class="small">{d}</td><td class="small">{s}</td></tr>'
        for i, cls, t, d, s in IRREG)
    body = f"""
<div class="panel">
<h2 style="margin-top:0;border:0">Flagged irregularities</h2>
<p>Nothing below is hidden: these are the places where the brief, the data or the instrument does
not support the claim that would otherwise be made.</p>
<table><tr><th>id</th><th></th><th>issue</th><th>detail</th><th>evidence</th></tr>{rows}</table>
</div>
"""
    return site.layout("Irregularities", body, "irregularities.html",
                       "Flagged, not asserted. ● red = blocker, amber = caveat, green = resolved.")


HAND_KEPT_PAGES = (
    # Merged PR #3 + PR #4 pages.  Never write these from the generator.
    "index.html",
    "executive-summary.html",
    "hypotheses.html",
    "research.html",
    "leaderboard.html",
    "sources.html",
    "mclp-line.html",
)


def main() -> int:
    pages = {
        # Only the MCLP-line irregularities page is still generated; the page_*
        # renderers for the hand-kept pages above are retained for reference but
        # MUST NOT be written back (see HAND_KEPT_PAGES).
        "irregularities.html": page_irreg(),
    }
    for name, html in pages.items():
        assert name not in HAND_KEPT_PAGES, f"refusing to overwrite hand-kept {name}"
        (DOCS / name).write_text(html)
        print(f"  wrote docs/{name} ({len(html):,} bytes)")
    print("  skipped hand-kept merged pages: " + ", ".join(HAND_KEPT_PAGES))
    # NOTE: docs/assets/site.css is the hand-kept light theme; do not overwrite
    # it with site.CSS (the generated pages are inline-styled and do not use it).
    (DOCS / ".nojekyll").write_text("")
    # site data feeds
    if pipe:
        (DOCS / "data" / "pipeline.json").write_text(json.dumps({
            "surfaces": {s: {"frames": e["frames"], "plan": e["emission_plan"]}
                         for s, e in pipe["surfaces"].items()}}, indent=1))
    if cal:
        (DOCS / "data" / "calibration.json").write_text(json.dumps(cal, indent=1))
    (DOCS / "data" / "leaderboard.json").write_text(json.dumps(
        {"read_utc": "2026-10-06", "rows": LEADERBOARD}, indent=1))
    render_research_pages()          # keeps the site's links to the research notes resolvable
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
