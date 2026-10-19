
from pathlib import Path

from pypdf import PdfReader


# Locate the project root and supplier PDF directory.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RFP_DATA_DIR = PROJECT_ROOT / "data" / "synthetic_rfps"


def get_rfp_path(filename: str) -> Path:
    """Validate and return the path to a supplier PDF."""

    data_dir = RFP_DATA_DIR.resolve()
    path = (data_dir / filename).resolve()

    # Prevent access to files outside the supplier PDF directory.
    if not path.is_relative_to(data_dir):
        raise ValueError("Invalid RFP file path.")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    if not path.is_file():
        raise FileNotFoundError(f"RFP file not found: {filename}")

    return path


def extract_text_from_pdf(file_path: str) -> str:
    """Extract readable text from all pages of a PDF."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    if not path.is_file():
        raise ValueError("The provided path is not a file.")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    reader = PdfReader(str(path))
    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    extracted_text = "\n".join(pages).strip()

    if not extracted_text:
        raise ValueError("No readable text found in the PDF.")

    return extracted_text
