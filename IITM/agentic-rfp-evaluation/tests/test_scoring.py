
import pytest

from src.rfp.services.scoring import calculate_weighted_score


def test_calculate_weighted_score():
    scores = {
        "Technical Capability": 8,
        "Implementation Plan": 7,
        "Commercial Value": 9,
        "Security & Compliance": 6,
        "Support & Experience": 8,
    }

    result = calculate_weighted_score(scores)

    assert result == 7.6


def test_all_scores_zero():
    scores = {
        "Technical Capability": 0,
        "Implementation Plan": 0,
        "Commercial Value": 0,
        "Security & Compliance": 0,
        "Support & Experience": 0,
    }

    assert calculate_weighted_score(scores) == 0.0


def test_all_scores_ten():
    scores = {
        "Technical Capability": 10,
        "Implementation Plan": 10,
        "Commercial Value": 10,
        "Security & Compliance": 10,
        "Support & Experience": 10,
    }

    assert calculate_weighted_score(scores) == 10.0
