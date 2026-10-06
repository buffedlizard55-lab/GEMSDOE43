# Three-pass release review — 2026-10-06

**Scope:** review of the H46-B source audit, one registered public-catalogue blocked-proxy run, the distinct research-only GeoTIFF, form note, README and static GitHub Pages source. This is a review record, not private-set validation or submission approval. H46-B's promotion gate failed; no slot was authorized.

## Pass 1 — method, code, reproducibility and file contract

- Confirmed the experiment recipe is frozen at `e020a9692f5263f958dff05910bb081dae50cc69`; later commits registered the workflow and added documentation/evidence, without changing the experiment code.
- Confirmed source-gate evidence from [SGMC Actions run 37455479306](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37455479306): exact hashes/bytes for the v1.1 CA, NV and table archives; declared CRS; field/join results; 12,469 transformed intersecting geometries; zero transform errors/warnings; full finite-footprint unit coverage; 96.3289% joint class support; 476,338 positive-contrast cells; zero outside-footprint signal. The selective loader did not extract/open either Structure layer.
- Confirmed the frozen implementation's local 17-test suite and compile check plus [Actions test/compile run 37455479404](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37455479404) passed. These are unit/engineering checks, not private-set validation.
- Reconciled the complete fold table with [`evidence/h46b/holdout.json`](../evidence/h46b/holdout.json): same-run H42 folds equal the prior values exactly; H46-B folds differ by `−0.000006`, `−0.000051`, `+0.001972`, `+0.001776`; mean delta `+0.000923`; 2/4 wins. The +0.005 mean and 3/4-win gates fail; the baseline and worst-fold gates pass. Overall promotion is false.
- Independently re-read the GeoTIFF with Rasterio and recalculated its file size/SHA-256: 381,558 bytes; SHA-256 `c51cf006c19f1993606a0b0b55467f0a74f0a1c13e747c3f592d55690d93a6f6`; one-band float32, 3730 × 3292, EPSG:32611, expected 100 m transform, NaN nodata, 5,167,373 finite-footprint cells, finite `[0,1]` values and 40,000 positive prediction pixels. Receipt matches. These checks establish file integrity/format only.
- Confirmed the GeoTIFF is produced by the registered code and pinned feature inputs, not copied from a sibling. Confirmed experiment surfaces were built before public-catalogue labels were used for the registered fold/guard/DTI operations. No private challenge labels were accessed.

**Pass 1 result:** method and format receipts are internally consistent; the artifact remains research-only and not cleared for upload.

## Pass 2 — source provenance, access, irregularities and website links

The following primary pages were manually opened during this review; the visible content matched the cited facts and source scope:

- DrivenData [problem and submission-format page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/): challenge target is expert-labelled new faults; the public catalogue is incomplete; required submission is a one-band 32-bit float GeoTIFF, EPSG:32611, 100 m, same bounds, outside cells null/NaN, inside confidence in `[0,1]`. The page distinguishes the private initial-prize set and final expert-reviewed label expansion.
- USGS NGB Open-File Report 2002-227 [data](https://pubs.usgs.gov/of/2002/0227/data.html), [metadata](https://pubs.usgs.gov/of/2002/0227/metadata.html) and [quality](https://pubs.usgs.gov/of/2002/0227/quality.html) pages: medium codes, coordinate/datum uncertainty, assay methods, source substitution notes and inter-study caveats were reviewed. The raw CSV link returned HTTP 500 to the final page-fetch request; the earlier source-audit runner did download and checksum-verify 2,318,363 bytes. The interface error is not presented as proof that the data are generally unavailable.
- USGS SGMC [state download index](https://mrdata.usgs.gov/geology/state/), [v1.1 metadata](https://mrdata.usgs.gov/geology/state/USGS_SGMC_Metadata.html), [geol_poly](https://mrdata.usgs.gov/geology/state/about.php?tblname=geol_poly), [age](https://mrdata.usgs.gov/geology/state/about.php?tblname=age), [lithology](https://mrdata.usgs.gov/geology/state/about.php?tblname=lith) and [units](https://mrdata.usgs.gov/geology/state/about.php?tblname=units) field pages; [USGS credit policy](https://www.usgs.gov/information-policies-and-instructions/acknowledging-or-crediting-usgs); official [ScienceBase catalog record](https://www.sciencebase.gov/catalog/item/5888bf4fe4b05ccb964bab9d) listing the separate CSV table archive; and both the 2017 v1.1 [DOI](https://doi.org/10.5066/F7WH2N65) and the newly recommended 2026 GeMS [DOI](https://doi.org/10.5066/P1A3DQZK)/[NGMDB product record](https://ngmdb.usgs.gov/Prodesc/proddesc_119417.htm).
- USGS [Landsat Collection 2](https://www.usgs.gov/landsat-missions/landsat-collection-2) page: confirms program-level Level-2 data availability, not project-specific scene coverage or reuse terms.
- Official leaderboard URL was opened, but this page-fetch view returned only the JavaScript “Loading” shell. A separate sandbox `curl` attempt failed TLS. The 2026-10-06 row values remain date-bound observations from the earlier live review; no screenshot, raw page capture, or file/hash crosswalk is represented. See [`evidence/leaderboard_observation.json`](../evidence/leaderboard_observation.json).
- GitHub Actions run links are backed by successful/complete GitHub run records; see the source, test and experiment receipts cited above.

**Important version caveat:** ScienceBase's older 2017 v1.1 catalog record now notes a 2026 update in a newer GeMS schema and recommends DOI `10.5066/P1A3DQZK`. H46-B remains an experiment on the pinned, preregistered 2017 v1.1 archives; the newer release was not fetched or audited and was not silently substituted. Any follow-on must pass its own source audit and fresh confirmation test.

**Internal site check:** `PYTHONPATH=src .venv/bin/python scripts/check_site_links.py` passed: 32 repository-local links resolved across `index.html` and `knowledge-base.html`. The site links its Markdown project/research records to GitHub's rendered `main`-branch views (to avoid relying on Jekyll's Markdown output path); these links become current when this branch is merged. The HTML parser accepted both pages. The 17-test suite passed with four non-fatal Rasterio affine deprecation warnings; `compileall`, shell syntax checks and `git diff --check` passed.

**Pass 2 result:** primary sources and material version/access irregularities are documented; leaderboard data could not be freshly retrieved through the page-fetch path, so no undated/current-score claim is made.

## Pass 3 — claims, scope, disclosure and release readiness

- The homepage, knowledge base, README, evidence receipt and form note all use “public-catalogue blocked proxy” rather than private validation or a DrivenData score.
- The homepage and submission instructions prominently say **do not submit**; the form note states the failed gate; no submission slot or organizer upload is claimed.
- The 0.2778 rank-#13 and 0.3345 rank-#1 rows are dated 2026-10-06 and not attributed to a file. The lack of receipt/hash crosswalk is explicit; the later inability to refresh the JavaScript page is recorded.
- H46-A's failed source gate and H46-B's failed promotion gate remain distinct decisions. H46-C is marked untested; no silent hypothesis replacement or post-holdout tuning is presented.
- The newer 2026 GeMS release, NGB raw-CSV fetch response, SGMC separate age/lithology table archive, initial `SGMC_Lithology.csv`/`lith.csv` name mismatch, and non-opened Structure layers are disclosed.
- Competition feature and public-catalogue label data are described as owner-supplied mirrors, not organizer-authenticated originals. The private test labels and credentials are not in Git. The sample template contributes only grid/finite-mask metadata.
- AI-use disclosure states assistance scope and describes the TIFF as deterministic numerical output. The USGS SGMC credit and official competition/source links are present.
- No external service, tracking, CDN or font dependency is required to render the static site; the site uses local CSS and relative downloads.

**Pass 3 result:** public claims and upload status are conservative; the current artifact is not a contest submission. Publish the site only after the repository review/merge and successful Pages deployment are independently confirmed.
