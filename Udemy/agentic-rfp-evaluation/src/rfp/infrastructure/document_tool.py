from io import BytesIO
from pypdf import PdfReader
from rfp.config import settings
def extract_pdf_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes: raise ValueError("Uploaded PDF is empty.")
    if len(pdf_bytes)>settings.max_pdf_bytes: raise ValueError("PDF exceeds configured upload limit.")
    try:
        reader=PdfReader(BytesIO(pdf_bytes),strict=True)
        if reader.is_encrypted: raise ValueError("Encrypted PDFs are not supported.")
        text="\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except ValueError: raise
    except Exception as exc: raise ValueError(f"Unable to parse PDF: {exc}") from exc
    if not text: raise ValueError("No selectable text found; OCR is not implemented in this MVP.")
    return text[:settings.max_extracted_chars]
