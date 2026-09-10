"""Render a deterministic, self-contained HTML view of primary results."""

from __future__ import annotations

from html import escape
from typing import Any


def _difference_rows(differences: list[dict[str, Any]]) -> str:
    pass #TODO: Implement a simple table of differences

def _effect_chart(differences: list[dict[str, Any]]) -> str:
    pass #TODO: Implement a simple SVG chart to visualize the effects.

def render_html_report(
    summary: dict[str, Any],
    estimates: list[dict[str, Any]],
    differences: list[dict[str, Any]],
) -> str:
    # Rendering the primary JSON results as an accessible standalone HTML report.

    run_id = escape(str(summary["run_id"]))
    split = escape(str(summary["split"]))
    final = bool(summary["primary_results_final"])
    status = "Final" if final else "Awaiting adjudication"
    accepted = int(summary["accepted_observations"])
    invalid = int(summary["invalid_observations"])
    review_items = int(summary["review_items"])
    pending = int(summary["pending_metric_contributions"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Paired Agent Evaluation — {run_id}</title><style>
:root{{--ink:#172033;--muted:#62708a;--panel:#f5f7fb;--line:#dce2ec;--accent:#176b87}}
body{{font:15px/1.5 system-ui,sans-serif;color:var(--ink);max-width:1120px;
margin:auto;padding:2rem}} h1{{margin-bottom:.2rem}} .meta{{color:var(--muted)}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}}
.card{{background:var(--panel);padding:1rem;border-radius:8px}}
.card strong{{display:block;font-size:1.5rem}} table{{border-collapse:collapse;width:100%}}
th,td{{padding:.55rem;text-align:left;border-bottom:1px solid var(--line)}}
th{{background:var(--panel)}} svg{{width:100%;max-height:520px}}
svg rect{{fill:var(--accent)}} svg line{{stroke:var(--ink)}}
@media(max-width:700px){{.cards{{grid-template-columns:1fr 1fr}}}}
@media print{{body{{max-width:none}}}}
</style></head><body><main>
<h1>Paired Agent Evaluation</h1><p class="meta">Run {run_id} · {split} · {status}</p>
<section class="cards" aria-label="Run summary">
<div class="card">Accepted<strong>{accepted}</strong></div>
<div class="card">Invalid<strong>{invalid}</strong></div>
<div class="card">Review items<strong>{review_items}</strong></div>
<div class="card">Pending scores<strong>{pending}</strong></div>
</section><h2>Overall governed-minus-baseline effects</h2>{_effect_chart(differences)}
<h2>Paired differences</h2><table><thead><tr><th>Metric</th><th>Stratum</th>
<th>Effect</th><th>95% CI</th><th>Pairs</th></tr></thead>
<tbody>{_difference_rows(differences)}</tbody></table>
<p class="meta">Condition estimates: {len(estimates)}. Effects are descriptive unless the
preregistered protocol states otherwise.</p>
</main></body></html>"""
