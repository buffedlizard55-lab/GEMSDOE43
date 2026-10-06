# Submission status and conditional instructions

## Current result: no upload, no eligible download, no slot

**Do not submit H46-B.** The frozen recipe did not meet the preregistered public-catalogue promotion gate: mean `ΔDTI=+0.000923` versus a required `+0.005`, with 2/4 fold wins versus a required 3/4. It has not been evaluated on the challenge's private test set and has no DrivenData leaderboard score. No submission slot has been used or authorized.

The experiment runner generated a unique GeoTIFF and recorded its format/hash receipt; after the no-go decision, the file was removed from the current repository tree and is **not linked from the current project site**. An earlier public branch commit and unexpired GitHub Actions artifact still contain it; a deletion request returned HTTP 403 because the GitHub integration lacks permission. Do not download or submit that historical file. No DrivenData upload occurred. The identifier and SHA-256 remain in [`evidence/h46b/submission_receipt.json`](../evidence/h46b/submission_receipt.json); [`publication_status.json`](../evidence/h46b/publication_status.json) records the access/expiry caveat.

The short text in [`FORM-NOTE.txt`](FORM-NOTE.txt) is a research-status record only. It is not a portal submission note and must not be pasted into a form as if the artifact were eligible.

## If a future, separately authorized candidate passes

These are conditional instructions for a **new** artifact only; they do not authorize uploading the current H46-B file.

1. Freeze a new dated method/source amendment before validation. If the source or recipe changes, require fresh blocked confirmation regions; do not tune on H46-B's four evaluated folds.
2. Require a written promotion decision, passing format/independence/provenance checks, a new unique filename and SHA-256 receipt, and explicit authorization before spending a slot.
3. Read the organizer's current [GEMS Prize Challenge submission page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) immediately before any future upload; its current instructions supersede this general checklist.
4. Upload only an explicitly authorized GeoTIFF through the official interface. Use its exact registered submission name, paste the new concise note and AI-use disclosure, and save the platform receipt separately. Do not infer a per-file score without a verified receipt/hash crosswalk.
5. Record the date, run/commit, filename, byte count, SHA-256, format receipt, form text and official upload receipt. Never reuse a sibling's file or claim a score for an artifact without that crosswalk.

## AI-use disclosure for a future submission

AI coding assistance was used for source synthesis, implementation drafting, tests, experiment orchestration and documentation. A future raster from this workflow would be a deterministic numerical output of documented code applied to pinned data, not a generative image or hand-labelled fault map. No private challenge labels were accessed for this project.
