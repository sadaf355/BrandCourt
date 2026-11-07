from io import BytesIO
from zipfile import BadZipFile, ZipFile


def extract_guideline_text(suffix: str, raw: bytes) -> str:
    if suffix == ".txt":
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text guidelines must be UTF-8.") from exc
        if "\x00" in text:
            raise ValueError("Text guidelines contain invalid binary data.")
        return text

    if suffix == ".pdf":
        if not raw.startswith(b"%PDF-"):
            raise ValueError("File content does not match the PDF extension.")
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(raw)).pages)
        except (PdfReadError, ValueError, OSError) as exc:
            raise ValueError("File content is not a valid PDF document.") from exc

    if suffix == ".docx":
        try:
            with ZipFile(BytesIO(raw)) as archive:
                names = set(archive.namelist())
                if (
                    len(names) > 1000
                    or "[Content_Types].xml" not in names
                    or "word/document.xml" not in names
                    or sum(info.file_size for info in archive.infolist()) > 100 * 1024 * 1024
                ):
                    raise ValueError("File content is not a valid DOCX document.")
                if archive.testzip() is not None:
                    raise ValueError("File content is not a valid DOCX document.")
        except BadZipFile as exc:
            raise ValueError("File content does not match the DOCX extension.") from exc
        from docx import Document
        from docx.oxml.exceptions import InvalidXmlError
        from docx.opc.exceptions import PackageNotFoundError

        try:
            document = Document(BytesIO(raw))
        except (BadZipFile, InvalidXmlError, PackageNotFoundError, ValueError, KeyError) as exc:
            raise ValueError("File content is not a valid DOCX document.") from exc
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        paragraphs.extend(
            " | ".join(cell.text for cell in row.cells)
            for table in document.tables
            for row in table.rows
        )
        return "\n".join(paragraphs)

    raise ValueError("Unsupported guideline file type.")
