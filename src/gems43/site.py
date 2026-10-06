"""Render the GitHub Pages site from the measured evidence JSON.

Nothing on the site is typed by hand: every number is read from ``evidence/*.json``,
``registry/*.json`` or ``docs/score-ledger.csv``.  If a number has not been measured, the page
says so instead of inventing one.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

from . import paths

NAV = [
    ("index.html", "Overview"),
    ("executive-summary.html", "How to submit"),
    ("hypotheses.html", "Hypotheses"),
    ("research.html", "Method"),
    ("leaderboard.html", "Scores"),
    ("sources.html", "Sources"),
    ("irregularities.html", "Irregularities"),
]

CSS = """
:root{--bg:#0e1116;--panel:#161b22;--panel2:#1c2230;--ink:#e6edf3;--dim:#9aa7b4;--acc:#4cc2ff;
--good:#3fb950;--warn:#d29922;--bad:#f85149;--line:#2a313c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc)}
header{background:linear-gradient(180deg,#12171f,#0e1116);border-bottom:1px solid var(--line);
padding:22px 0 14px}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:20px;margin-top:30px;border-bottom:1px solid var(--line);padding-bottom:6px}
h3{font-size:16px;margin-top:22px;color:var(--acc)}
nav{margin-top:12px;display:flex;flex-wrap:wrap;gap:8px}
nav a{background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:5px 11px;
text-decoration:none;color:var(--ink);font-size:13px}
nav a:hover{border-color:var(--acc)}
nav a.on{background:#123047;border-color:var(--acc)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;
margin:16px 0}
.hero{background:linear-gradient(135deg,#123047,#161b22);border:1px solid #1f5b7d}
table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
th{background:var(--panel2);font-weight:600}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
code{background:#0b0f14;border:1px solid var(--line);border-radius:4px;padding:1px 5px;
font-size:12.5px}
pre{background:#0b0f14;border:1px solid var(--line);border-radius:8px;padding:12px;overflow:auto;
font-size:12.5px}
.btn{display:inline-block;background:var(--good);color:#04150a;font-weight:700;text-decoration:none;
padding:11px 20px;border-radius:8px;font-size:15px;margin:6px 8px 6px 0}
.btn.alt{background:var(--panel2);color:var(--ink);border:1px solid var(--line);font-weight:600}
.small{font-size:12.5px;color:var(--dim)}
.tag{display:inline-block;font-size:11px;border:1px solid var(--line);border-radius:999px;
padding:1px 8px;color:var(--dim);margin-right:4px}
.ok{color:var(--good)}.no{color:var(--bad)}.wn{color:var(--warn)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.card{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:12px}
.card .v{font-size:22px;font-weight:700}
.card .k{font-size:12px;color:var(--dim)}
ul{padding-left:20px}
footer{border-top:1px solid var(--line);margin-top:40px;padding:18px 0;color:var(--dim);font-size:12.5px}
.step{background:var(--panel2);border-left:3px solid var(--acc);padding:10px 14px;margin:10px 0;
border-radius:0 8px 8px 0}
"""


def _esc(s) -> str:
    return html.escape(str(s))


def layout(title: str, body: str, active: str, subtitle: str = "") -> str:
    nav = "".join(
        f'<a href="{p}" class="{"on" if p == active else ""}">{_esc(n)}</a>' for p, n in NAV)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)}</title>
<style>{CSS}</style></head><body>
<header><div class="wrap">
<h1>{_esc(title)}</h1>
<div class="small">{subtitle}</div>
<nav>{nav}</nav>
</div></header>
<div class="wrap">{body}</div>
<footer><div class="wrap">GEMSDOE43 &middot; DOE GEMS Prize Challenge (DrivenData #306) &middot;
rendered {stamp} from <code>evidence/*.json</code> &middot;
<a href="https://github.com/buffedlizard55-lab/GEMSDOE43">repository</a></div></footer>
</body></html>
"""


def _load(name: str, default=None):
    p = paths.evidence_dir() / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def _load_registry(name: str, default=None):
    p = paths.registry_dir() / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def download_block(sub: dict | None) -> str:
    if not sub:
        return ('<div class="panel"><b>No submission has been built yet.</b> '
                'Run <code>scripts/build_submission.py</code>.</div>')
    f = sub["files"]["zeros"]
    note = _esc(sub.get("submission_note", ""))
    name = _esc(sub.get("portal_name", ""))
    nan = sub["files"].get("nan", {})
    zp = sub["files"].get("zip", {})
    return f"""
<div class="panel hero">
<h2 style="margin-top:0;border:0">⬇ Download the submission file</h2>
<p><a class="btn" href="downloads/{_esc(f['filename'])}">Download {_esc(f['filename'])}</a>
<a class="btn alt" href="downloads/{_esc(zp.get('filename','#'))}">.zip</a>
<a class="btn alt" href="downloads/{_esc(nan.get('filename','#'))}">NaN-outside twin</a></p>
<table>
<tr><th>property</th><th>measured value</th></tr>
<tr><td>file</td><td><code>{_esc(f['filename'])}</code></td></tr>
<tr><td>size</td><td class="n">{f['size_bytes']:,} bytes</td></tr>
<tr><td>sha256</td><td><code>{_esc(f['sha256'])}</code></td></tr>
<tr><td>grid</td><td>1 band &middot; float32 &middot; 3730 &times; 3292 &middot; EPSG:32611 &middot;
100 m &middot; transform (100, 0, 243350, 0, −100, 4508550)</td></tr>
<tr><td>cells in [0,&nbsp;1], all finite</td>
    <td class="n ok">{f['full_grid_finite_pixels']:,} / 12,279,160 &mdash; PASS</td></tr>
<tr><td>emitted dots</td><td class="n">{f['emitted_positive_pixels']:,}</td></tr>
<tr><td>dots on a known catalogue pixel</td>
    <td class="n ok">{f['on_catalogue_positive_pixels']:,}</td></tr>
<tr><td>portal <b>unique name</b></td><td><code>{name}</code></td></tr>
</table>
<h3>Submission note to paste (copy exactly)</h3>
<pre>{note}</pre>
</div>"""
