import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rfp.config import get_local_api_key
from src.rfp.infrastructure.document_reader import (
    extract_text_from_pdf,
    get_rfp_path,
)
from src.rfp.infrastructure.llm_client import evaluate_supplier


def main():
    api_key = get_local_api_key()

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is missing. Check your .env file."
        )

    # Step 1: Read one supplier PDF.
    pdf_path = get_rfp_path("Apex_Systems.pdf")
    proposal_text = extract_text_from_pdf(str(pdf_path))

    print(f"Extracted {len(proposal_text)} characters from PDF.")

    # Step 2: Call OpenAI to evaluate the proposal.
    result = evaluate_supplier(
        proposal_text=proposal_text,
        api_key=api_key,
        model="gpt-4.1-mini",
    )

    # Step 3: Display the structured result.
    print("\nSupplier:", result.supplier_name)

    for item in result.evaluations:
        print(f"\nCriterion: {item.criterion}")
        print(f"Score: {item.score}/10")
        print(f"Justification: {item.justification}")
        print(f"Evidence: {item.evidence}")


if __name__ == "__main__":
    main()
