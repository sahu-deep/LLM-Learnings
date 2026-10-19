
CRITERIA_WEIGHTS = {
    "Technical Capability": 0.30,
    "Implementation Plan": 0.20,
    "Commercial Value": 0.20,
    "Security & Compliance": 0.20,
    "Support & Experience": 0.10,
}


def calculate_weighted_score(scores: dict[str, int]) -> float:
    """Calculate a validated weighted supplier score."""

    expected_criteria = set(CRITERIA_WEIGHTS)
    supplied_criteria = set(scores)

    missing = expected_criteria - supplied_criteria
    unexpected = supplied_criteria - expected_criteria

    if missing:
        raise ValueError(f"Missing criteria: {sorted(missing)}")

    if unexpected:
        raise ValueError(f"Unexpected criteria: {sorted(unexpected)}")

    for criterion, score in scores.items():
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError(f"Invalid score for {criterion}")

        if not 0 <= score <= 10:
            raise ValueError(f"Score for {criterion} must be between 0 and 10")

    total = sum(
        scores[criterion] * weight
        for criterion, weight in CRITERIA_WEIGHTS.items()
    )

    return round(total, 2)
