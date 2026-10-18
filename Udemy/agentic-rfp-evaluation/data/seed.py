from rfp.infrastructure.database import initialize_database,connection,DEFAULT_CRITERIA
def reseed():
    initialize_database()
    with connection() as conn:
        conn.execute("DELETE FROM evaluation_criteria")
        conn.executemany("INSERT INTO evaluation_criteria(criterion_id,name,description,weight,max_score,is_active) VALUES(?,?,?,?,?,?)",DEFAULT_CRITERIA)
    print("Seeded 5 criteria; weights total 100%.")
if __name__=="__main__": reseed()
