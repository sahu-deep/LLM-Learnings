import json
import uuid

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATABASE_DIR / "rfp_evaluations.db"


def get_connection() -> sqlite3.Connection:
    """Create a connection to the SQLite database."""

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database() -> None:
    """Create the database tables if they do not exist."""

    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_name TEXT NOT NULL UNIQUE,
                submission_date TEXT,
                experience_rating REAL
                    CHECK (
                        experience_rating IS NULL
                        OR experience_rating BETWEEN 0 AND 10
                    )
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                weighted_score REAL NOT NULL
                    CHECK (weighted_score BETWEEN 0 AND 10),
                overall_summary TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id)
                    REFERENCES suppliers(supplier_id)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS criterion_assessments (
                assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER NOT NULL,
                criterion TEXT NOT NULL,
                score REAL NOT NULL CHECK (score BETWEEN 0 AND 10),
                justification TEXT NOT NULL,
                evidence TEXT NOT NULL,
                FOREIGN KEY (evaluation_id)
                    REFERENCES evaluations(evaluation_id),
                UNIQUE (evaluation_id, criterion)
            )
        """)
        
        connection.execute("""
            CREATE TABLE IF NOT EXISTS rfp_runs (
                rfp_run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'IN_PROGRESS'
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS supplier_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rfp_run_id TEXT NOT NULL,
                supplier_name TEXT NOT NULL,
                submission_date TEXT,
                experience_rating REAL,
                absolute_score REAL NOT NULL,
                ppi REAL,
                final_rank INTEGER,
                result_json TEXT NOT NULL,
                FOREIGN KEY (rfp_run_id)
                    REFERENCES rfp_runs(rfp_run_id)
            )
        """)


def save_evaluation(
    supplier_name: str,
    weighted_score: float,
    assessments: list[dict],
    submission_date: str | None = None,
    experience_rating: float | None = None,
    overall_summary: str | None = None,
) -> int:
    """Save a supplier evaluation and its criterion assessments."""

    with get_connection() as connection:
        # Insert supplier or update its metadata.
        connection.execute(
            """
            INSERT INTO suppliers (
                supplier_name, submission_date, experience_rating
            )
            VALUES (?, ?, ?)
            ON CONFLICT(supplier_name) DO UPDATE SET
                submission_date = excluded.submission_date,
                experience_rating = excluded.experience_rating
            """,
            (supplier_name, submission_date, experience_rating),
        )

        row = connection.execute(
            "SELECT supplier_id FROM suppliers WHERE supplier_name = ?",
            (supplier_name,),
        ).fetchone()

        supplier_id = row["supplier_id"]

        # Store this evaluation run.
        cursor = connection.execute(
            """
            INSERT INTO evaluations (
                supplier_id, weighted_score, overall_summary
            )
            VALUES (?, ?, ?)
            """,
            (supplier_id, weighted_score, overall_summary),
        )

        evaluation_id = cursor.lastrowid

        # Store each criterion assessment.
        for assessment in assessments:
            connection.execute(
                """
                INSERT INTO criterion_assessments (
                    evaluation_id, criterion, score,
                    justification, evidence
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    evaluation_id,
                    assessment["criterion"],
                    assessment["score"],
                    assessment["justification"],
                    assessment["evidence"],
                ),
            )

        return evaluation_id


def create_rfp_run() -> str:
    """Create a new evaluation batch and return its run ID."""
    run_id = f"RFP-{uuid.uuid4().hex[:10].upper()}"

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO rfp_runs (rfp_run_id, status)
            VALUES (?, 'IN_PROGRESS')
            """,
            (run_id,),
        )

    return run_id


def save_run_results(
    run_id: str,
    ranked_results: list[dict],
) -> None:
    """Save the complete ranked supplier results for one batch."""

    with get_connection() as connection:
        for result in ranked_results:
            connection.execute(
                """
                INSERT INTO supplier_results (
                    rfp_run_id,
                    supplier_name,
                    submission_date,
                    experience_rating,
                    absolute_score,
                    ppi,
                    final_rank,
                    result_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    result["supplier_name"],
                    result["submission_date"],
                    result["experience_rating"],
                    result["weighted_score"],
                    result["ppi"],
                    result["final_rank"],
                    json.dumps(result, ensure_ascii=False),
                ),
            )

        connection.execute(
            """
            UPDATE rfp_runs
            SET status = 'COMPLETED'
            WHERE rfp_run_id = ?
            """,
            (run_id,),
        )


def get_previous_runs() -> list[dict]:
    """Return evaluation runs, newest first."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                r.rfp_run_id,
                r.created_at,
                r.status,
                COUNT(s.result_id) AS supplier_count,
                (
                    SELECT s2.supplier_name
                    FROM supplier_results s2
                    WHERE s2.rfp_run_id = r.rfp_run_id
                    ORDER BY s2.final_rank ASC
                    LIMIT 1
                ) AS top_supplier
            FROM rfp_runs r
            LEFT JOIN supplier_results s
                ON s.rfp_run_id = r.rfp_run_id
            GROUP BY r.rfp_run_id
            ORDER BY r.created_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_run_results(run_id: str) -> list[dict]:
    """Load the saved supplier scorecards for a previous run."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT result_json
            FROM supplier_results
            WHERE rfp_run_id = ?
            ORDER BY final_rank ASC
            """,
            (run_id,),
        ).fetchall()

    return [json.loads(row["result_json"]) for row in rows]
