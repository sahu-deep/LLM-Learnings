
from pydantic import ValidationError

from src.rfp.domain.models import CriterionEvaluation


def test_valid_score():
    evaluation = CriterionEvaluation(
        criterion="Technical Capability",
        score=8,
        justification="Strong technical solution.",
        evidence="The proposal describes the required integration.",
    )

    assert evaluation.score == 8


def test_invalid_score():
    try:
        CriterionEvaluation(
            criterion="Technical Capability",
            score=11,
            justification="Test",
            evidence="Test evidence",
        )
        assert False, "Expected validation to fail"
    except ValidationError:
        pass
