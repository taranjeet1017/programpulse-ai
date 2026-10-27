from io import BytesIO
from pypdf import PdfReader
from .models import IngestionError
from .safety import MAX_TEXT


def read_pdf(data: bytes) -> tuple[str, int]:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise IngestionError("status_report", "encrypted")
        if len(reader.pages) > 50:
            raise IngestionError("status_report", "resource_limit")
        parts = []
        total = 0
        for page in reader.pages:
            content = page.get_contents()
            if content is not None and len(content.get_data()) > 2_000_000:
                raise IngestionError("status_report", "resource_limit")
            text = page.extract_text() or ""
            total += len(text)
            if total > MAX_TEXT:
                raise IngestionError("status_report", "resource_limit")
            parts.append(text)
        text = "\n".join(parts)
        if sum(c.isalnum() for c in text) < 40:
            raise IngestionError("status_report", "pdf_text")
        return text, len(reader.pages)
    except IngestionError:
        raise
    except Exception:
        raise IngestionError("status_report", "malformed") from None
