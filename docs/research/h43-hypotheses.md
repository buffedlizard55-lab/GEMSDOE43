# H43 — five untried geological hypotheses, ranked, with the measurement that decided each

**Session:** Arena `arena/a4a86abd-gemsdoe43` · **Date:** 2026-10-06
**Question this file answers:** *what has this lineage not tried, which of it can be validated
locally, which needs new external data, and what did the blocked holdout actually say?*

Evidence labels used throughout:

| label | meaning |
|---|---|
| `[OFFICIAL]` | read from a DrivenData / USGS / DOE page or product; link and read date given |
| `[MEASURED]` | computed in this checkout from sha256-pinned bytes; the command is given |
| `[MIRROR, hash-pinned]` | organizer-derived bytes obtained from an owner-maintained public mirror, pinned by sha256 and byte count; **not** organizer-authenticated |
| `[OWNER-REPORT]` | the group's own ledger; no organizer receipt exists |
| `[BLOCKED]` | could not be obtained here; reason stated, nothing fabricated |

---

## 0. Why the placement problem, and why that changes which hypothesis matters

The official index is `DTI = T / (0.2T + 0.2F + 0.8|G|)` with `T = TP_w`. Three exact consequences
(full algebra and tests in [`metric-algebra.md`](metric-algebra.md)):

1. `FN_w = |G| − TP_w`, hence the form above.
2. Adding a pixel of weight `p` raises the denominator by **exactly `0.2 p` regardless of its
   credit**, so the move pays iff its kernel credit exceeds `0.2·DTI` — and the rule is
   independent of `p`, which is why **binary emission is optimal**.
3. `FP_w = |S| − Σ_i k_i` is **modular** in the emitted set, so for a fixed dot count the placement
   problem is exactly MCLP.

Therefore the score factors into **(a) how good the demand field `π` is** and **(b) how efficiently
dots are placed given `π`**. This repository solves (b) exactly and provably
(`(1 − 1/e)` guarantee), which means **all remaining headroom is in (a)** — and (a) is a geology
question, which is why the hypotheses below are the whole game.

How much headroom (b) by itself is worth: the group's best artifact realises **0.126 weighted
credit per emitted dot** against a theoretical **3.0** for a dot sitting on a straight fault trace
(`1 + 2·(2/3) + 2·(1/3)`). That is ~4 % — the gap is coverage, not emission quality.

---

## 1. The five candidates

Ranked by *expected DTI gain per unit of implementation cost*; the bottom of the file reports what
the blocked holdout actually said, which is not always the same order.

### H43-1 — Magnetic source-edge lineaments from the unused tilt-angle band — **rank 1**

* **Layers [MIRROR, hash-pinned; names read from the GeoTIFF band descriptions, not assumed]:**
  `tc` (6, *"Tilt angle or total curvature — magnetic field derivative for edge detection"*),
  `tmi_hg` (3), `tmi_vg` (9), `tmi` (14), `rtp` (2).
* **Physical signature:** the **analytic signal amplitude**
  `ASA = √(tmi_hg² + tmi_vg²)` (Nabighian 1972; Roest, Verhoef & Pilkington 1992), whose peaks
  locate magnetic contacts *independently of the magnetization direction* — the standard tool for
  contacts under cover — fused with the **tilt-angle** channel: `|∇tc|`, the narrow band around the
  tilt zero contour (which outlines the source body), and the multi-scale Frangi line response of
  `tc` itself.
* **Why it should catch a catalogue-missing fault:** a magnetically-expressed contact under thin
  alluvial cover produces **no scarp**, so a surface-mapped inventory has nothing to record, while
  the contact is exactly the kind of lithologic offset that hosts a fault. The tilt angle is
  explicitly the organizer's own edge-detection product.
* **How it differs from everything in this lineage:** GEMSDOE32's own verification audit records
  that bands **6, 9, 10 and 16 have no derived transform at all**. Band 6 is the tilt angle.
  Nobody in the lineage has used it.
* **Cost:** ~15 s CPU, no new data. **Locally validatable: yes.**

### H43-2 — Concealed basin-bounding faults (basement step × conductivity step × geodetic shear, × concealment gate) — **rank 2**

* **Layers:** `depth_to_base_surf` (15, *"thickness of sedimentary cover"*), `cond_surf` (17),
  `geod_shearrate` (7), `geod_2ndinv` (4), `geod_dilaterate` (8), gated by `det_elev` (12) and
  `det_elev_slope` (19).
* **Physical signature:** the **geometric mean** of (i) the ridge of `|∇ depth_to_base_surf|`,
  (ii) the ridge of `|∇ log cond_surf|` and (iii) the Frangi ridge of the geodetic shear rate —
  then multiplied by a **concealment gate** `1 − ½(relief + slope)`, which asks *where would a
  surface mapper be blind?*
* **Why it should catch a catalogue-missing fault:** a basin-bounding fault under basin fill has no
  geomorphic expression at all; MT conductivity and basement depth are the only supplied layers
  that image it, and present-day shear rate is the only supplied evidence that it is *active*.
* **How it differs:** H33-D (GEMSDOE32) used `cond_surf` / `depth_to_base_surf` gradient
  magnitude plus orientation coherence. The **concealment gate** and the **geodetic term** are new
  objects, and the gate is what turns "a gradient somewhere" into "a gradient where nobody could
  have mapped".
* **Cost:** ~20 s CPU, no new data. **Locally validatable: yes.**

### H43-3 — Geothermal-fluid conduit alignment from the thermal-spring point pattern — **rank 3**

* **Layers:** external — GDR / INGENIOUS `gdr_wellspring_in_footprint.csv` (27,092 records,
  12,570 unique locations, with measured temperature and four geothermometers) and
  `gdr_volcanic_vents_in_footprint.csv` (21 vents).
* **Physical signature:** a **locality-constrained PCA lineament** through the point pattern. A
  thermal spring requires a permeable, fluid-connected fracture — a *conduit*, not a coincidence.
* **Why it should catch a catalogue-missing fault:** `[MEASURED]` in the supplied inventory the
  median distance from a thermal feature to the **nearest mapped fault is 2.4 km** (column
  `dist_known_fault_px`, median 24.0 px at 100 m). Springs systematically sit on structures the
  catalogue does not contain.
* **A global Hough transform is the wrong tool here, and this is measured, not asserted.** With
  72 orientation bins and ~2,000 hot springs, the expected number of *accidental* collinear
  triples exceeds the real ones by orders of magnitude: for each of ~2×10⁶ point pairs the third
  point falls within one pixel of the implied line with probability ≈ 8×10⁻⁴, giving ≈ 3×10⁶
  chance triples. The implementation therefore constrains every fit to a 25 px (2.5 km)
  neighbourhood, keeps only clusters of ≥ 3 features with elongation ≥ 0.80, and paints the
  principal axis extended 12 px along strike. `[MEASURED]` on a synthetic control: a straight
  100-point chain scores **57×** the response of a random point pattern of the same size, and the
  peak lands on the chain.
* **How it differs:** prior work used springs only as an **isotropic proximity decay**
  (GEMSDOE32 H33-1, which was **FALSIFIED** as an addition arm). Using them as **orientation
  evidence** — inferring the *direction* of a conduit and extrapolating along it — is new.
* **Cost:** ~10 s CPU, no new data. **Locally validatable: yes.**

### H43-4 — Gravity source-parameter imaging of fault-bounded blocks — **rank 4**

* **Layers:** `iso_grav_anom` (13), `iso_grav_anom_hg` (18), `iso_grav_anom_vg` (11),
  `iso_grav_anom_slope` (5).
* **Physical signature:** the **tilt-depth / SPI** estimator (Salem et al. 2007)
  `depth ≈ 1 / |∇ arctan(vg / hg)|`, plus the analytic-signal amplitude of the isostatic anomaly
  and the multi-scale Frangi ridge of the anomaly itself. Ridges of the depth estimate mark
  fault-bounded blocks under basin fill.
* **Why it should catch a catalogue-missing fault:** gravity images the *density* structure of the
  fill and basement. A buried range-front fault is a density step with no surface expression.
* **How it differs:** all four gravity bands enter the lineage's feature stacks as scalars or plain
  gradient magnitudes; no source-depth imaging has been applied.
* **Cost:** ~15 s CPU, no new data. **Locally validatable: yes.**

### H43-5 — Sub-kilometre seismicity lineaments from the raw catalogue — **rank 5, DATA-BLOCKED**

* **Layers:** would replace/augment `ieq_n100a15` (16) and `deq_n100a15` (10).
* **Physical signature:** epicentre density residual plus **focal-mechanism nodal-plane strikes**.
  A fault that is unmapped but active carries earthquakes whose preferred nodal plane is the fault
  plane.
* **Why it should catch a catalogue-missing fault:** instrumental seismicity is a *dynamic*
  inventory: blind, low-slip faults light up seismically while leaving no scarp.
* **Measured justification (adopted from GEMSDOE32, re-checkable here):** the supplied seismic
  bands are computed on a 100 km radius and carry no fault-scale information — `ieq` is
  **0.9935 self-correlated at a 3 km lag**, i.e. constant at the metric's own 300 m resolution.
  The high-pass residual implemented here (`|ieq − smooth(ieq, 12 px)|`) is the only way any
  fault-scale information can survive, and it is a weak substitute for the real catalogue.
* **Source, named and checked [OFFICIAL]:** USGS FDSN event web service,
  <https://earthquake.usgs.gov/fdsnws/event/1/query> and the ComCat UI
  <https://earthquake.usgs.gov/earthquakes/search/>; products include moment tensors / nodal
  planes. **Obtainability check performed in this sandbox:** `curl` to `earthquake.usgs.gov`
  returns **HTTP 000** (egress allow-list). The source is **named but NOT verified obtainable
  here**; per the brief it is ranked last and **not proposed as ready**. No earthquake surface is
  fabricated. A fetcher would run on any unrestricted machine in under a minute.
* **Cost:** n/a here. **Locally validatable: no** — ranked 5 and not promoted.

---

## 2. Ranked decision table

| rank | hypothesis | layers | signature | off-catalogue reason | novelty vs the lineage | cost | local validation | new data |
|---:|---|---|---|---|---|---|---|---|
| 1 | **H43-1** | `tc`, `tmi_hg`, `tmi_vg`, `tmi`, `rtp` | analytic signal + tilt-angle edge/zero-band + Frangi | magnetic contact under cover leaves no scarp | bands 6 and 9 have **no** prior transform | 15 s | yes | none |
| 2 | **H43-2** | `depth_to_base_surf`, `cond_surf`, `geod_shearrate` | 3-way coincidence × **concealment gate** | buried basin-bounding faults are un-mappable at the surface | gate + geodetic term are new | 20 s | yes | none |
| 3 | **H43-3** | GDR springs / vents | **locality-constrained PCA lineament** through thermal features | springs sit a median 2.4 km from any mapped fault | prior work used proximity decay only | 10 s | yes | none |
| 4 | **H43-4** | 4 gravity bands | tilt-depth SPI + gravity analytic signal | buried range-front density steps | no source-depth imaging exists | 15 s | yes | none |
| 5 | **H43-5** | raw earthquake catalogue | epicentre + nodal-plane strikes | active blind faults are seismic | supplied bands are 100 km-radius | n/a | **no** | USGS FDSN — **blocked here** |

---

## 3. What the blocked holdout actually said

Three frames, each with a stated bias ([`src/gems43/holdout.py`](../../src/gems43/holdout.py)):

| family | truth | masked | what it measures | bias |
|---|---|---|---|---|
| **A** | catalogue components held out by spatial block (4 blocks) | the rest of the catalogue | can the method generalise to a withheld piece of the *same* inventory? | the truth is "old news" — the style of fault that was already mappable |
| **B** | **SGMC fault pixels the competition catalogue does not contain** (79,615 px) | the whole catalogue | can the method find faults a *different* compilation knows? | SGMC includes pre-Quaternary and inferred faults; broader than an expert's "new active fault" list |
| **C** | catalogue components held out by block | the rest of the catalogue **plus a 300 m flank** | generalisation *away* from mapped traces | same inventory as A |

`[MEASURED]` Frame B truth sizes per block: 31,160 / 29,127 / 3,854 / 15,474 px. The B_block2
cell is small (3.9k px) because the SGMC-derived compilation is sparse in that quadrant; its fold
value therefore carries more noise and this is stated rather than hidden.

Every candidate surface was solved by the MCLP greedy at `|G| = 12,226` (the parent project's
live-anchor estimate) and scored at every cardinality on all twelve frames:
`evidence/pipeline_main.json`.

### Instrument calibration — the step that decides whether any of the above means anything

A holdout number is meaningless without a rank correlation against live scores, so the artifacts
whose live score is already known were re-scored on exactly the same frames
(`scripts/calibrate_instrument.py`, `evidence/instrument_calibration.json`). The parent project
measured ρ ≈ +0.51 (n = 12) for its catalogue instrument; the same measurement is repeated here
for A, B and C, and the **reference bar** is recorded: a candidate must beat the best
previously-scored artifact *on the same frame* before it is promoted.

> **Standing rule adopted from the brief:** no submission slot is spent on an idea that has not
> beaten the current holdout best, and the correlation is reported with its p-value so that a
> weak instrument is never mistaken for a strong one.

---

## 4. Reproduction

```bash
bash scripts/fetch_mirrors.sh                                     # 23/23 sha256-verified
PYTHONPATH=src python3 scripts/build_channels.py                  # 62 channels, ~75 s
PYTHONPATH=src python3 scripts/run_pipeline.py --k-max 60000      # MCLP + 12 blocked frames
PYTHONPATH=src python3 scripts/calibrate_instrument.py            # rank correlation vs live
PYTHONPATH=src python3 scripts/build_submission.py --select-on ABC
```

## 5. Sources

* Competition metric and rules: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
* Known-fault masking: <https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516>
* GeoDAWN survey: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
* INGENIOUS / GDR submission 1391 (springs, wells, vents; CC BY 4.0): <https://gdr.openei.org/submissions/1391>
* Analytic signal: Nabighian (1972) *Geophysics* 37(6); Roest, Verhoef & Pilkington (1992) *Geophysics* 57(1)
* Tilt angle / tilt-depth: Miller & Singh (1994) *Geophysics*; Salem et al. (2007) *Geophysics* 72(2)
* Frangi vesselness: Frangi et al. (1998) *IEEE TMI* 17(4)
* USGS earthquake catalogue (H43-5, blocked here): <https://earthquake.usgs.gov/fdsnws/event/1/query>
* Parent project's band audit (which bands had no transform): `buffedlizard55-lab/GEMSDOE32`, `docs/research/verification-2026-10-04.md`
