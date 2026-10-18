from types import SimpleNamespace
from unittest.mock import Mock, patch

from rfp.infrastructure.llm import evaluate_proposal


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
