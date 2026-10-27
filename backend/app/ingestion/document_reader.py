from .models import StatusReportDocument, IngestionError
from .docx_reader import read_docx
from .pdf_reader import read_pdf
from .safety import decode_text, MAX_TEXT


def read_document(filename: str, extension: str, data: bytes) -> StatusReportDocument:
    pages = None
    warnings = []
    if extension == ".docx":
        text = read_docx(data)
        warnings.append("Body paragraphs and tables extracted; headers, footers and text boxes are not included.")
    elif extension == ".pdf":
        text, pages = read_pdf(data)
        warnings.append("Embedded text only; visual reading order can differ. No OCR performed.")
    else:
        text = decode_text(data, "status_report")
    if not text.strip():
        raise IngestionError("status_report", "empty")
    if len(text) > MAX_TEXT:
        raise IngestionError("status_report", "resource_limit")
    return StatusReportDocument(filename=filename, file_type=extension.lstrip("."),
        extracted_text=text, character_count=len(text), page_count=pages, warnings=warnings,
        source_metadata={"extraction": "embedded text", "filename": filename})
