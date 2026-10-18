# Agentic RFP Evaluation & Supplier Ranking
Streamlit app to assess supplier RFP PDFs, validate LLM output, calculate deterministic weighted scores and peer benchmarks, rank suppliers, persist results in SQLite, and export JSON.

## Demo warning
Without an API key, `RFP_DEMO_MODE=true` uses a keyword heuristic. This is NOT LLM evaluation and must not be used for real procurement decisions. To use the LLM, enter an API key in the app sidebar or set `OPENAI_API_KEY` in `.env`.

## Setup (Python 3.11+, PowerShell)
```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env
```
The app lets you enter an OpenAI API key in the sidebar and choose a chat model.
The key field is masked and the entered key is used for the current Streamlit
session. Alternatively, set `OPENAI_API_KEY` in `.env` and leave the field blank.
Keep `.env` private. `OPENAI_MODEL` sets the default model selected when the app
starts.

## Run
```powershell
python scripts/init_db.py
python -m streamlit run src/rfp/main.py
```
Four fictional PDFs are in `data/synthetic_rfps/`. Upload at least two.

## Formulas
Absolute score = sum((score / max score) * weight), out of 100.
Benchmark = highest criterion score in batch. Gap = score - benchmark.
Relative performance = score / benchmark * 100, or zero if benchmark is zero.
PPI = weighted average of criterion relative performance.
Tie-break: higher PPI, earlier submission date, higher experience rating, supplier name ascending.

## Tests
`pytest`

## Commercial readiness
This is an MVP foundation, not production-certified. Before commercial use add authentication, authorization, tenant isolation, malware scanning, encryption, retention controls, OCR, human approval, observability, cost controls, database migrations, load testing, and security/privacy review.
