
import sqlite3

from src.rfp.infrastructure.database import (
    get_connection,
    initialize_database,
    save_evaluation,
)


def test_initialize_database():
    initialize_database()

    from src.rfp.infrastructure.database import DATABASE_PATH

    assert DATABASE_PATH.exists()

    with sqlite3.connect(DATABASE_PATH) as connection:
        tables = {
            row[0]
            for row in connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
            """)
        }

    assert "suppliers" in tables
    assert "evaluations" in tables
    assert "criterion_assessments" in tables








def test_save_evaluation(tmp_path, monkeypatch):
    import src.rfp.infrastructure.database as database

    test_db = tmp_path / "test.db"

    monkeypatch.setattr(database, "DATABASE_PATH", test_db)
    monkeypatch.setattr(database, "DATABASE_DIR", tmp_path)

    initialize_database()

    evaluation_id = save_evaluation(
        supplier_name="Apex Systems",
        weighted_score=7.6,
        assessments=[
            {
                "criterion": "Technical Capability",
                "score": 8,
                "justification": "Strong technical solution.",
                "evidence": "Proposal describes the integration architecture.",
            }
        ],
    )

    assert evaluation_id > 0

    with sqlite3.connect(test_db) as connection:
        row = connection.execute(
            "SELECT weighted_score FROM evaluations WHERE evaluation_id = ?",
            (evaluation_id,),
        ).fetchone()

    assert row[0] == 7.6
