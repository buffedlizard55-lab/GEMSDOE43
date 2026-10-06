# SGMC table-archive follow-up — 2026-10-06

The first official download and schema inspection succeeded for both state ZIPs, but the audit did **not** reach polygon coverage or any holdout. GitHub Actions run [`37447558793`](https://github.com/buffedlizard55-lab/GEMSDOE43/actions/runs/37447558793) retrieved these official files over HTTPS:

| Archive | Bytes | SHA-256 |
|---|---:|---|
| California `CA.zip` | 24,977,406 | `78765ba4428df9f25a84f86e0b2529bd0508fc8a2cf65d2f41a830e82bccfd58` |
| Nevada `NV.zip` | 69,056,094 | `3b333ac025e59aae7f0d827db45ba32c425cf867eb341561a788af1de186b76b` |

The official state archives contain the `CA_geol_poly` / `NV_geol_poly` polygon layers, state `*_lith.csv` and `*_units.csv` tables, and structure layers. They **do not contain `age.csv`**, so the original loader's assumption that each state ZIP carried the standard age table was wrong. The loader stopped at that schema error. No polygon rasterization, class-coverage result, candidate surface, fold score, or submission was produced. The audit code uses only the polygon layer and does not open the structure layer.

### Explicit same-release source correction

The official SGMC download index separately offers the all-state attribute-table archive [`USGS_SGMC_Tables_CSV.zip`](https://www.sciencebase.gov/catalog/file/get/5888bf4fe4b05ccb964bab9d?name=USGS_SGMC_Tables_CSV.zip), listed as 1.6 MB. It belongs to the same USGS SGMC version 1.1 / DOI `10.5066/F7WH2N65`; it is not a replacement geological dataset. Before any holdout, the next source-only audit will retrieve and hash this archive, verify the actual age/lith table names and fields, and join the documented `state + unit_link` keys to the CA/NV polygons. It will still stop if any of the predeclared ≥90% polygon-coverage, ≥60% joined lithology-and-age coverage, or ≥5,000 positive-contact-cell gates fail.

The all-state table archive itself was also fetched over HTTPS in run `37454198095`: 1,573,709 bytes, SHA-256 `8859dd1f00ec6ec3d397634dc86fa288e440b432aad8a98a5fb0c7f9b6bc0bde`. It contains `SGMC_Age.csv` and `SGMC_Lithology.csv` (not a file named `lith.csv`). The next audit update maps the documented `Lithology` table name and then checks actual table fields and joins. This second schema stop occurred before geometry processing.

This amendment corrects a distribution-layout assumption transparently. H46-B remains pending and unscored. No private labels, sample-template pixel values, fault-score layer, known-fault geometry, or submission slot has been used.
