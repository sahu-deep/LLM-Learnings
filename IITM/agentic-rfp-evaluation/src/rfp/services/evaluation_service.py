
from src.rfp.infrastructure.document_reader import (
    extract_text_from_pdf,
    get_rfp_path,
)
from src.rfp.infrastructure.database import (
    initialize_database,
    save_evaluation,
)
from src.rfp.infrastructure.llm_client import evaluate_supplier
from src.rfp.services.scoring import calculate_weighted_score


def evaluate_supplier_pdf(
    filename: str,
    api_key: str,
    model: str = "gpt-4.1-mini",
) -> dict:
    """Extract, evaluate, score, and save one supplier proposal."""

    # 1. Resolve the PDF path.
    pdf_path = get_rfp_path(filename)

    # 2. Extract proposal text.
    proposal_text = extract_text_from_pdf(str(pdf_path))

    # 3. Evaluate proposal content with the LLM.
    evaluation = evaluate_supplier(
        proposal_text=proposal_text,
        api_key=api_key,
        model=model,
    )

    # 4. Calculate the weighted score in Python.
    scores = {
        item.criterion: item.score
        for item in evaluation.evaluations
    }

    weighted_score = calculate_weighted_score(scores)

    # 5. Initialize the database and save the evaluation.
    initialize_database()

    evaluation_id = save_evaluation(
        supplier_name=evaluation.supplier_name,
        weighted_score=weighted_score,
        assessments=[
            item.model_dump()
            for item in evaluation.evaluations
        ],
    )

    # 6. Return the evaluation result.
    return {
        "evaluation_id": evaluation_id,
        "supplier_name": evaluation.supplier_name,
        "scores": scores,
        "weighted_score": weighted_score,
        "evaluations": [
            item.model_dump()
            for item in evaluation.evaluations
        ],
    }
