from io import BytesIO
from zipfile import ZipFile

import pytest
from docx import Document
from pypdf import PdfWriter

from app.core.guideline_files import extract_guideline_text


def test_guideline_text_requires_valid_utf8_and_rejects_binary_bytes():
    assert extract_guideline_text(".txt", b"Keep claims evidence-based.") == (
        "Keep claims evidence-based."
    )
    with pytest.raises(ValueError, match="UTF-8"):
        extract_guideline_text(".txt", b"\xff")
    with pytest.raises(ValueError, match="binary"):
        extract_guideline_text(".txt", b"\x00")


def test_guideline_pdf_requires_pdf_signature_and_parses_valid_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = BytesIO()
    writer.write(buffer)

    assert extract_guideline_text(".pdf", buffer.getvalue()) == ""
    with pytest.raises(ValueError, match="match the PDF"):
        extract_guideline_text(".pdf", b"PK\x03\x04not pdf")


def test_guideline_docx_requires_office_document_parts():
    document = Document()
    document.add_paragraph("Approved claims need evidence.")
    buffer = BytesIO()
    document.save(buffer)

    assert "Approved claims need evidence." in extract_guideline_text(
        ".docx", buffer.getvalue()
    )
    with pytest.raises(ValueError, match="match the DOCX"):
        extract_guideline_text(".docx", b"not a zip file")

    fake_docx = BytesIO()
    with ZipFile(fake_docx, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/not-document.xml", "<document/>")
    with pytest.raises(ValueError, match="valid DOCX"):
        extract_guideline_text(".docx", fake_docx.getvalue())
