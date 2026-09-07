from pathlib import Path

from conftest import BaselineAnswerModel, GovernedAnswerModel, StaticRetriever

from paired_agent_evaluation.adapters.systems import BaselineSystemRunner, GovernedSystemRunner
from paired_agent_evaluation.application.normalization import normalize
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.domain.executions import Condition


def test_both_frozen_systems_run_against_isolated_shared_fixture(
    tmp_path: Path, settings, answer_case
) -> None:
    schedule = build_schedule([answer_case], repetitions=1, seed=20260831)
    by_condition = {item.key.condition: item for item in schedule}
    baseline = BaselineSystemRunner(
        settings,
        retriever_factory=lambda _: StaticRetriever(),
        model_factory=lambda _: BaselineAnswerModel(),
    ).execute(answer_case, by_condition[Condition.BASELINE], tmp_path / "baseline")
    governed = GovernedSystemRunner(
        settings,
        retriever_factory=lambda _: StaticRetriever(),
        model_factory=lambda _: GovernedAnswerModel(),
    ).execute(answer_case, by_condition[Condition.GOVERNED], tmp_path / "governed")
    assert baseline.request_accepted is True
    assert governed.request_accepted is True
    assert baseline.request == governed.request
    assert baseline.state_before == governed.state_before
    assert governed.audit_events
    assert normalize(baseline).route_requires_adjudication is True
    assert normalize(governed).observed_route.value == "answer"
