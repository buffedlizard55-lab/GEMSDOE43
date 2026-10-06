#!/usr/bin/env python3
"""Build the derived channel stack. Usage: PYTHONPATH=src python3 scripts/build_channels.py"""
import sys, time, json
import numpy as np
from gems43 import bands, channels, paths

t0 = time.time()
foot = bands.footprint()
cat = bands.catalogue()
print(f"footprint {foot.sum():,}  catalogue {cat.sum():,}", flush=True)
st = channels.build(foot, cat)
meta = st.save()
print(json.dumps({"n_channels": len(st.names), "shape": meta["shape"],
                  "seconds": round(time.time() - t0, 1)}, indent=1))
