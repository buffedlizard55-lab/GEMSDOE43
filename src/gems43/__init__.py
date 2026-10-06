"""GEMSDOE43 — maximal-covering (MCLP) emission for the DOE GEMS prize challenge.

Package map
-----------
``paths``       data/work/docs/evidence/registry resolution
``grid``        the frozen competition grid (EPSG:32611, 100 m, 3730x3292) and helpers
``metric``      the official distance-weighted Tversky index, implemented verbatim
``bands``       readers for the 19 official bands and the hash-pinned external rasters
``features``    derived geophysical channels (lineament / curvature / coincidence transforms)
``surface``     prior (demand) surfaces pi(x) for the covering problem
``mclp``        Church--ReVelle maximal covering location problem solver (exact greedy + CELF)
``emitter``     budget selection by the exact marginal-credit / Dinkelbach fixed point
``holdout``     spatially blocked validation frames (catalogue, SGMC off-catalogue, GDR)
``submission``  fail-closed GeoTIFF writer + independent re-read verification
``novelty``     near-duplicate layout screening against the prior GEMSDOE submission corpus
"""
