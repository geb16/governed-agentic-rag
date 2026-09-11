"""Render primary evaluation results as deterministic standalone HTML.

Dynamic text is escaped before entering HTML or SVG contexts. The report includes
tabular paired effects, a bounded visual summary, run finality, and print styles.

References:
    [1] W3C WAI, "Providing Accessible Names and Descriptions."
        https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/
    [2] MDN Web Docs, "table," "SVG," "CSS grid layout," and "Using media queries."
        https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/table
        https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/svg
        https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Grid_layout
        https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Media_queries/Using
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any


def _number(value: Any) -> str:
    """Formats a numeric result or an em dash for a missing value."""
    return "—" if value is None else f"{float(value):.3f}"


def _difference_rows(differences: list[dict[str, Any]]) -> str:
    """Renders escaped paired-difference table rows in input order."""
    return "".join(
        "<tr>"
        f"<td>{escape(str(item['metric_id']))}</td>"
        f"<td>{escape(str(item['stratum']))}</td>"
        f"<td>{_number(item['governed_minus_baseline'])}</td>"
        f"<td>[{_number(item['ci_lower'])}, {_number(item['ci_upper'])}]</td>"
        f"<td>{int(item['complete_pairs'])}</td>"
        "</tr>"
        for item in differences
    )


def _effect_chart(differences: list[dict[str, Any]]) -> str:
    """Renders an accessible SVG chart for defined overall effects.

    Bar geometry is clamped to the metric range of -1 to 1; the table retains the
    authoritative values supplied in the input.
    """
    overall = [item for item in differences if item["stratum"] == "overall"]
    rows = []
    for index, item in enumerate(overall):
        effect = item["governed_minus_baseline"]
        if effect is None:
            continue
        value = max(-1.0, min(1.0, float(effect)))
        width = abs(value) * 220
        x = 300 if value >= 0 else 300 - width
        y = 24 + index * 38
        label = escape(str(item["metric_id"]))
        rows.append(
            f'<text x="8" y="{y + 15}">{label}</text>'
            f'<rect x="{x:.1f}" y="{y}" width="{width:.1f}" height="20" rx="3">'
            f"<title>{label}: {value:.3f}</title></rect>"
        )
    height = max(70, 40 + len(overall) * 38)
    return (
        f'<svg viewBox="0 0 540 {height}" role="img" aria-label="Overall paired effects">'
        f'<line x1="300" y1="8" x2="300" y2="{height - 8}"/>' + "".join(rows) + "</svg>"
    )


def render_html_report(
    summary: dict[str, Any],
    estimates: list[dict[str, Any]],
    differences: list[dict[str, Any]],
) -> str:
    """Renders an escaped, self-contained report from primary result records.

    Args:
        summary: Run identity, finality, and observation-count fields.
        estimates: Condition estimates; only their count is displayed.
        differences: Paired effects and confidence intervals to display.

    Returns:
        A complete UTF-8-compatible HTML document with inline CSS and SVG.

    Raises:
        KeyError: If a required result field is missing.
        TypeError: If a displayed numeric field cannot be converted.
        ValueError: If a displayed numeric field has an invalid value.
    """

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


def write_html_report(run_root: Path) -> Path:
    """Writes report.html from a run's authoritative primary JSON files.

    Args:
        run_root: Directory containing summary, estimate, and paired-difference
            artifacts.

    Returns:
        Path to the generated HTML report.

    Raises:
        OSError: If an input cannot be read or the report cannot be written.
        ValueError: If an input is invalid JSON or contains invalid numeric data.
        KeyError: If a required result field is missing.
    """

    def read(name: str) -> Any:
        return json.loads((run_root / name).read_text(encoding="utf-8"))

    output = run_root / "report.html"
    output.write_text(
        render_html_report(
            read("summary.json"), read("estimates.json"), read("paired-differences.json")
        ),
        encoding="utf-8",
        newline="\n",
    )
    return output
