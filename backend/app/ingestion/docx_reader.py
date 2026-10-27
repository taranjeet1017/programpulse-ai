from io import BytesIO
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from .models import IngestionError
from .safety import check_zip, MAX_TEXT


def read_docx(data: bytes) -> str:
    check_zip(data, "status_report")
    try:
        document = Document(BytesIO(data))
        lines = []
        for block in document.iter_inner_content():
            if isinstance(block, Paragraph):
                lines.append(block.text)
            elif isinstance(block, Table):
                for row in block.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    # Two-column metadata tables become the same explicit header syntax.
                    if len(cells) == 2 and cells[0].rstrip(":") in {
                        "Project", "Reporting date", "Reported overall health", "Target production release"
                    }:
                        lines.append(cells[0].rstrip(":") + ": " + cells[1])
                    else:
                        lines.append(" | ".join(cells))
        text = "\n".join(lines)
        if len(text) > MAX_TEXT:
            raise IngestionError("status_report", "resource_limit")
        return text
    except IngestionError:
        raise
    except Exception:
        raise IngestionError("status_report", "malformed") from None
