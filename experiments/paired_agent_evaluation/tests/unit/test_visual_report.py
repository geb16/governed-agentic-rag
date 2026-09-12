"""Verify security and accessibility properties of the standalone HTML report."""

from paired_agent_evaluation.reporting.visual_report import render_html_report


def test_visual_report_is_accessible_printable_and_escapes_result_labels() -> None:
    """Render accessible, printable HTML while escaping data-derived labels."""
    summary = {
        "run_id": "run_test",
        "split": "test",
        "accepted_observations": 2,
        "invalid_observations": 0,
        "pending_metric_contributions": 0,
        "review_items": 1,
        "primary_results_final": True,
    }
    differences = [
        {
            "metric_id": "unsafe_<script>",
            "stratum": "overall",
            "governed_minus_baseline": 0.25,
            "ci_lower": 0.1,
            "ci_upper": 0.4,
            "complete_pairs": 1,
        }
    ]

    report = render_html_report(summary, [], differences)

    assert "<!doctype html>" in report
    assert 'role="img"' in report
    assert "@media print" in report
    assert "unsafe_&lt;script&gt;" in report
    assert "unsafe_<script>" not in report
