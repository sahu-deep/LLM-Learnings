
from src.rfp.config import get_local_api_key
from src.rfp.services.evaluation_service import evaluate_supplier_pdf


SUPPLIER_FILES = [
    "Apex_Systems.pdf",
    "BrightPath_Tech.pdf",
    "NexaWorks.pdf",
    "Orbit_Digital.pdf",
]


def main():
    api_key = get_local_api_key()

    if not api_key:
        raise ValueError("OpenAI API key is missing.")

    results = []

    for filename in SUPPLIER_FILES:
        print(f"\nEvaluating {filename}...")

        result = evaluate_supplier_pdf(
            filename=filename,
            api_key=api_key,
        )

        results.append(result)

        print(f"Supplier: {result['supplier_name']}")
        print(f"Weighted score: {result['weighted_score']}/10")

    results.sort(
        key=lambda item: item["weighted_score"],
        reverse=True,
    )

    print("\n===== SUPPLIER RANKING =====")

    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. {result['supplier_name']} - "
            f"{result['weighted_score']}/10"
        )


if __name__ == "__main__":
    main()
