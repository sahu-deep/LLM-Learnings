CREATE TABLE IF NOT EXISTS evaluation_criteria (
 criterion_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL,
 weight REAL NOT NULL CHECK(weight >= 0 AND weight <= 100), max_score REAL NOT NULL CHECK(max_score > 0),
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)), updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rfp_runs (
 rfp_run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('RUNNING','COMPLETED','FAILED')), error_message TEXT
);
CREATE TABLE IF NOT EXISTS supplier_results (
 result_id INTEGER PRIMARY KEY AUTOINCREMENT,
 rfp_run_id TEXT NOT NULL REFERENCES rfp_runs(rfp_run_id) ON DELETE CASCADE,
 supplier_name TEXT NOT NULL, submission_date TEXT NOT NULL, experience_rating REAL NOT NULL,
 absolute_score REAL NOT NULL, ppi REAL NOT NULL, final_rank INTEGER NOT NULL,
 result_json TEXT NOT NULL, UNIQUE(rfp_run_id,supplier_name), UNIQUE(rfp_run_id,final_rank)
);
CREATE INDEX IF NOT EXISTS idx_supplier_results_run ON supplier_results(rfp_run_id);
