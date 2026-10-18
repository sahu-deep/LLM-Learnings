from datetime import date
from typing import Any
from pydantic import BaseModel, Field
class SupplierMetadata(BaseModel):
    supplier_name: str = Field(min_length=1, max_length=150)
    submission_date: date
    experience_rating: float = Field(ge=0, le=10)
class CriterionAssessment(BaseModel):
    criterion_id: int
    score: float
    max_score: float
    justification: str = ""
    evidence: str = ""
class EvaluationResult(BaseModel):
    supplier_name: str
    criteria: list[CriterionAssessment]
    risks: list[str] = []
    overall_summary: str = ""
    warnings: list[str] = []
class SupplierEvaluation(BaseModel):
    metadata: SupplierMetadata
    result: EvaluationResult
    absolute_score: float = 0
    ppi: float = 0
    final_rank: int | None = None
    criterion_metrics: list[dict[str, Any]] = []
