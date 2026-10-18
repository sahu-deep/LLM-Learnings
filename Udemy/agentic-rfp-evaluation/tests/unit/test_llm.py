from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from rfp.infrastructure.llm import demo_evaluation, evaluate_proposal


def test_evaluate_proposal_uses_provided_api_key_and_model():
    client = Mock()
    client.chat.completions.create.return_value.choices = [
        SimpleNamespace(message=SimpleNamespace(content='{"criteria": []}'))
    ]
    criteria = [
        {
            "criterion_id": 1,
            "name": "Technical Capability",
            "description": "Technical fit",
            "weight": 100,
            "max_score": 10,
        }
    ]

    with patch("rfp.infrastructure.llm.OpenAI", return_value=client) as openai:
        result = evaluate_proposal(
            "Supplier A",
            "Proposal text",
            criteria,
            api_key="test-api-key",
            model="gpt-test-model",
        )

    openai.assert_called_once_with(api_key="test-api-key", timeout=60, max_retries=2)
    assert client.chat.completions.create.call_args.kwargs["model"] == "gpt-test-model"
    assert result["supplier_name"] == "Supplier A"


def test_mock_mode_uses_heuristic_even_when_api_key_is_provided():
    criteria = [{"criterion_id": 1, "name": "Technical", "max_score": 10}]

    with patch("rfp.infrastructure.llm.OpenAI") as openai:
        result = evaluate_proposal(
            "Supplier A",
            "Architecture and integration details",
            criteria,
            api_key="test-api-key",
            evaluation_mode="mock",
        )

    openai.assert_not_called()
    assert result == demo_evaluation(
        "Supplier A", "Architecture and integration details", criteria
    )


def test_ai_mode_requires_api_key_even_when_demo_mode_is_enabled():
    with (
        patch("rfp.infrastructure.llm.settings.api_key", None),
        patch("rfp.infrastructure.llm.settings.demo_mode", True),
    ):
        with pytest.raises(
            RuntimeError, match="OpenAI API key is required for AI-powered evaluation"
        ):
            evaluate_proposal(
                "Supplier A",
                "Proposal text",
                [],
                evaluation_mode="ai",
            )
