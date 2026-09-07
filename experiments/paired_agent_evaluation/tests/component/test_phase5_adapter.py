from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import Phase5Dataset
from paired_agent_evaluation.application.scheduling import build_schedule


def test_frozen_splits_build_expected_paired_schedule(paths) -> None:
    dataset = Phase5Dataset(paths.repository)
    validation = dataset.cases(DatasetSplit.VALIDATION)
    test = dataset.cases(DatasetSplit.TEST)
    assert len(validation) == 20
    assert len(test) == 80
    assert len(build_schedule(validation, repetitions=3, seed=20260831)) == 120
    assert len(build_schedule(test, repetitions=3, seed=20260831)) == 480
