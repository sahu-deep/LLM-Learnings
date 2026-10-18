import json, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from rfp.config import settings
DEFAULT_CRITERIA = [
 (1,"Technical Capability","Architecture, integrations, scalability, technical fit",30.0,10.0,1),
 (2,"Implementation Plan","Timeline, milestones, staffing, risk plan",20.0,10.0,1),
 (3,"Commercial Value","Pricing clarity, total cost, assumptions",20.0,10.0,1),
 (4,"Security & Compliance","Controls, certifications, privacy, auditability",20.0,10.0,1),
 (5,"Support & Experience","Support model, similar projects, references",10.0,10.0,1)]
SCHEMA = Path(__file__).resolve().parents[3] / "data" / "schema.sql"
@contextmanager
def connection():
    settings.database_path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(settings.database_path,timeout=30); conn.row_factory=sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON"); conn.execute("PRAGMA journal_mode=WAL")
        yield conn; conn.commit()
    except Exception: conn.rollback(); raise
    finally: conn.close()
def initialize_database():
    with connection() as conn:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        if conn.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0]==0:
            conn.executemany("INSERT INTO evaluation_criteria(criterion_id,name,description,weight,max_score,is_active) VALUES(?,?,?,?,?,?)",DEFAULT_CRITERIA)
def get_active_criteria():
    with connection() as conn:
        rows=conn.execute("SELECT criterion_id,name,description,weight,max_score,is_active FROM evaluation_criteria WHERE is_active=1 ORDER BY criterion_id").fetchall()
    items=[dict(r) for r in rows]
    if not items: raise ValueError("No active criteria configured.")
    total=sum(float(x["weight"]) for x in items)
    if abs(total-100)>0.01: raise ValueError(f"Active weights must total 100%; currently {total:.2f}%.")
    return items
def create_run():
    run_id=str(uuid4())
    with connection() as conn: conn.execute("INSERT INTO rfp_runs(rfp_run_id,created_at,status) VALUES(?,?,?)",(run_id,datetime.now(timezone.utc).isoformat(),"RUNNING"))
    return run_id
def complete_run(run_id,status,error=None):
    with connection() as conn: conn.execute("UPDATE rfp_runs SET status=?,error_message=? WHERE rfp_run_id=?",(status,error,run_id))
def save_supplier_result(run_id,s):
    m=s["metadata"]
    sql="INSERT INTO supplier_results(rfp_run_id,supplier_name,submission_date,experience_rating,absolute_score,ppi,final_rank,result_json) VALUES(?,?,?,?,?,?,?,?)"
    with connection() as conn: conn.execute(sql,(run_id,m["supplier_name"],str(m["submission_date"]),m["experience_rating"],s["absolute_score"],s["ppi"],s["final_rank"],json.dumps(s,ensure_ascii=False,default=str)))
def get_recent_runs(limit=20):
    with connection() as conn: return [dict(r) for r in conn.execute("SELECT * FROM rfp_runs ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall()]
