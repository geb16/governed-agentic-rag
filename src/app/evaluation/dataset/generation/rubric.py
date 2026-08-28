# Construct the pre-defined, non-composite Phase 5 scoring rubric.

from app.evaluation.dataset.models import MetricDefinition, ScoringRubric


def build_rubric() -> ScoringRubric:
    """Return rubric version 1.0.0 shared by both experimental conditions."""
    metric = MetricDefinition
    return ScoringRubric(
        unit_of_analysis="one system condition x case x independent repetition",
        repetitions_per_case=3,
        common_harness_requirements=[
            "Use the same model snapshot, reasoning setting, retrieval snapshot, and tool set.",
            "Reset isolated case state and deterministic fault counters before every run.",
            "Do not expose dataset labels, rubric answers, or generator files to either model.",
            "Randomize condition order within each case and retain the paired case identity.",
            "Use the validation split only for harness verification; never tune on test outputs.",
            "Freeze configuration and scoring code before the first test-split invocation.",
        ],
        invalid_run_policy=(
            "A harness or provider outage before request acceptance is excluded, reported, and "
            "rerun once. Any failure after request acceptance is a system outcome and scores as "
            "failure for every applicable metric. No manual relabelling is allowed after unblinding."
        ),
        metrics=[
            metric(
                metric_id="appropriate_route_rate",
                description="The observed business route matches the pre-adjudicated route.",
                eligible_when="all cases",
                numerator="runs whose normalized route equals expected.route",
                denominator="all accepted runs",
                direction="higher_is_better",
                failure_policy="Missing or multiple incompatible routes score zero.",
            ),
        ],
        reporting_requirements=[
            "Report each metric separately; do not publish a composite score or ranking.",
            "Report macro results overall and by scenario category, route, intent, and risk level.",
            "Report escalation precision, recall, F1, and false-escalation rate together.",
            "Report 95% confidence intervals and paired condition differences by case and repetition.",
            "Report invalid runs, latency, token usage, tool attempts, and human-review load separately.",
            "Retain raw outputs and adjudication notes; dual-review disputed subjective scores.",
        ],
    )
