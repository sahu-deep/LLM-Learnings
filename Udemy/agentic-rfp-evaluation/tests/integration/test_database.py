from rfp.infrastructure.database import initialize_database,get_active_criteria
def test_criteria_seeded():
    initialize_database(); criteria=get_active_criteria()
    assert len(criteria)==5 and sum(c["weight"] for c in criteria)==100
