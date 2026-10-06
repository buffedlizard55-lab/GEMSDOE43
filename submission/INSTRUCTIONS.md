# Artifact identification and submission status

**Current status: do not upload this artifact.** The frozen H46-B recipe did not meet its preregistered public-catalogue promotion gate: mean `ΔDTI=+0.000923` against a required `+0.005`, with 2/4 fold wins against a required 3/4. It has not been evaluated on the challenge's private test set and has no DrivenData leaderboard score. No submission slot has been used or authorized.

The file is preserved for audit/reproduction, not promoted as an eligible entry:

- **Unique artifact:** [`GEMSDOE43-H46B-SGMC-H42CONTACT-40K-20261006.tif`](../docs/downloads/GEMSDOE43-H46B-SGMC-H42CONTACT-40K-20261006.tif)
- **Distinct identifier:** `GEMSDOE43-H46B-SGMC-H42CONTACT-40K-20261006`
- **SHA-256:** `c51cf006c19f1993606a0b0b55467f0a74f0a1c13e747c3f592d55690d93a6f6`
- **Format receipt:** [`evidence/h46b/submission_receipt.json`](../evidence/h46b/submission_receipt.json)

The exact concise note associated with this research artifact is in [`FORM-NOTE.txt`](FORM-NOTE.txt). It deliberately discloses the failed gate and says the file is not cleared for submission. Do not remove that context or describe the file as validated, privately scored, or leaderboard-scored.

## If a future, separately authorized candidate passes

These are conditional instructions for a **new** artifact only; they do not authorize uploading the current H46-B file.

1. Freeze a new dated method/source amendment before any new validation; require a fresh blocked confirmation if the recipe changes. Do not tune on the four H46-B folds.
2. Require the experiment's written promotion decision, passing format/independence checks, a new distinct filename and SHA-256 receipt, and explicit authorization to spend a slot.
3. Read the organizer's current [GEMS Prize Challenge submission page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) immediately before upload; its current instructions supersede this repository's general checklist.
4. Upload only the authorized unique GeoTIFF through the official competition interface, use its exact registered submission name, paste the new concise form note and AI-use disclosure, and save the platform receipt and resulting leaderboard row separately. A leaderboard row is not a per-file receipt unless the organizer provides a verifiable file crosswalk.
5. Record the date, run/commit, filename, byte count, SHA-256, format receipt, form text and official upload receipt. Never reuse a sibling's file or claim a score for an artifact without that crosswalk.

## AI-use disclosure

AI coding assistance was used for source synthesis, implementation drafting, tests, experiment orchestration and documentation. The raster is a deterministic output of the documented numerical workflow applied to pinned geology/feature data; it is not a generative image or a hand-labelled fault map. Source access, code, checksums, fold results and the no-promotion decision are recorded in the repository. No private challenge labels were accessed.
