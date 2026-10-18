from rfp.validation import validate_and_normalize
CRITERIA=[{"criterion_id":1,"name":"Technical","weight":60,"max_score":10},{"criterion_id":2,"name":"Commercial","weight":40,"max_score":10}]
def test_missing_filled_and_score_clipped():
    r=validate_and_normalize({"criteria":[{"criterion_id":1,"score":15}]},"Supplier A",CRITERIA)
    assert r.criteria[0].score==10 and r.criteria[1].score==0 and len(r.warnings)>=2
