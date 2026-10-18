from rfp.infrastructure.database import initialize_database,get_active_criteria
if __name__=="__main__":
    initialize_database()
    print("Database initialized")
    for c in get_active_criteria(): print(f"{c['criterion_id']}. {c['name']}: {c['weight']}%")
