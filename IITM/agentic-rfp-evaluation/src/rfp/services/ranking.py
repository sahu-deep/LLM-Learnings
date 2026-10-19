
from datetime import date

from src.rfp.services.scoring import CRITERIA_WEIGHTS


def benchmark_and_rank(suppliers: list[dict]) -> list[dict]:
    if not suppliers:
        return []

    criteria = list(CRITERIA_WEIGHTS)

    benchmarks = {
        criterion: max(
            supplier["scores"][criterion]
            for supplier in suppliers
        )
        for criterion in criteria
    }

    results = []

    for supplier in suppliers:
        gaps = {}
        relative = {}

        for criterion in criteria:
            score = supplier["scores"][criterion]
            benchmark = benchmarks[criterion]

            gaps[criterion] = round(score - benchmark, 2)
            relative[criterion] = (
                round(score / benchmark * 100, 2)
                if benchmark > 0
                else 100.0
            )

        ppi = round(
            sum(
                relative[c] * CRITERIA_WEIGHTS[c]
                for c in criteria
            ),
            2,
        )

        results.append({
            **supplier,
            "benchmarks": benchmarks,
            "gaps": gaps,
            "relative_performance": relative,
            "ppi": ppi,
        })

    results.sort(
        key=lambda item: (
            -item["weighted_score"],
            -item["ppi"],
            date.fromisoformat(item["submission_date"]),
            -item["experience_rating"],
            item["supplier_name"].casefold(),
        )
    )

    for rank, result in enumerate(results, start=1):
        result["final_rank"] = rank

    return results
