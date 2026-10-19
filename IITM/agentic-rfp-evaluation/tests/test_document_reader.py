
from src.rfp.infrastructure.document_reader import (
    extract_text_from_pdf,
    get_rfp_path,
)


def test_read_apex_proposal():
    pdf_path = get_rfp_path("Apex_Systems.pdf")
    text = extract_text_from_pdf(str(pdf_path))

    assert len(text) > 0
    print(text[:500])
