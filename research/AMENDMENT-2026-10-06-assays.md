# H46-A assay-field amendment — 2026-10-06

**Filed before any H46-A sample-quality report, feature raster, or holdout result was computed.** The first official-endpoint probe established only an HTTPS 200 response, byte count (2,318,363), and the CSV header; its legacy `DictReader` schema check failed on the source's blank-name qualifier columns, so it yielded no usable source statistics. The raw response is not in the repository.

The preregistration now fixes the trace-element assay fields to `Ag(part)_ppm`, `As(part)_ppm`, `Au_AA`, `Pb(part)_ppm`, `Sb(part)_ppm`, and `Zn(part)_ppm`. This selection follows the official USGS metadata: ICP-Partial is the lower-detection-limit trace-element method, and Au is reported by graphite-furnace atomic adsorption. The data page states that substituted values are marked by `*` in the next column. The code will parse the CSV positionally and exclude marked/censored/non-numeric values. This is a data-schema/measurement-quality refinement only; no element values, spatial coverage counts, catalogue labels, folds, or candidate results were inspected when selecting the fields.

- Official metadata: https://pubs.usgs.gov/of/2002/0227/metadata.html
- Official method / qualification notes: https://pubs.usgs.gov/of/2002/0227/quality.html
- Official data table / substitution notes: https://pubs.usgs.gov/of/2002/0227/data.html
- Source schema and filter code: `src/gemsdoe43/geochem.py`
- Holdout protocol and promotion gate remain unchanged: `research/PREREGISTRATION-2026-10-06.md`
