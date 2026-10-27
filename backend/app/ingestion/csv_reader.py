import csv
from io import StringIO
from .models import IngestionError
from .safety import decode_text, MAX_ROWS, MAX_COLUMNS


def read_csv(data: bytes, field: str) -> tuple[str | None, list[tuple[int, list]]]:
    text = decode_text(data, field)
    try:
        rows = []
        for index, row in enumerate(csv.reader(StringIO(text), strict=True), 1):
            if index > MAX_ROWS + 1 or len(row) > MAX_COLUMNS:
                raise IngestionError(field, "resource_limit")
            if any(cell.strip() for cell in row):
                rows.append((index, row))
        return None, rows
    except csv.Error:
        raise IngestionError(field, "malformed") from None
