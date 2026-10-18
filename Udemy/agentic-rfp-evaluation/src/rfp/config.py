import os
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
class Settings:
    api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    database_path = Path(os.getenv("DATABASE_PATH", str(ROOT / "data" / "rfp_evaluation.db")))
    demo_mode = os.getenv("RFP_DEMO_MODE", "true").lower() in {"1","true","yes"}
    max_pdf_bytes = int(os.getenv("MAX_PDF_BYTES", "15000000"))
    max_extracted_chars = int(os.getenv("MAX_EXTRACTED_CHARS", "100000"))
settings = Settings()
