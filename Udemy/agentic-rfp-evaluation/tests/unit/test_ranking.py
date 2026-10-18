from datetime import date
from rfp.domain import SupplierMetadata,EvaluationResult,CriterionAssessment,SupplierEvaluation
from rfp.services import score_and_rank
CRITERIA=[{"criterion_id":1,"name":"Technical","weight":60.,"max_score":10.},{"criterion_id":2,"name":"Commercial","weight":40.,"max_score":10.}]
def make(name,t,c,day,exp):
    return SupplierEvaluation(metadata=SupplierMetadata(supplier_name=name,submission_date=date.fromisoformat(day),experience_rating=exp),result=EvaluationResult(supplier_name=name,criteria=[CriterionAssessment(criterion_id=1,score=t,max_score=10),CriterionAssessment(criterion_id=2,score=c,max_score=10)]))
def test_tie_break_and_absolute_score():
    ranked=score_and_rank([make("Beta",8,8,"2026-01-02",8),make("Alpha",8,8,"2026-01-01",7)],CRITERIA)
    assert [x.metadata.supplier_name for x in ranked]==["Alpha","Beta"]
    assert ranked[0].absolute_score==80
