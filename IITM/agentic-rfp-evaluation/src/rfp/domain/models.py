from pydantic import BaseModel, Field

class CriterionEvaluation(BaseModel):
    criterion: str
    score: int = Field(ge=0, le=10)
    justification: str
    evidence: str
    
class SupplierEvaluation(BaseModel):
    supplier_name: str
    evaluations: list[CriterionEvaluation]