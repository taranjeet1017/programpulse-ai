"""Bounded byte readers; no document content is executed or logged."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from .models import IngestionError

EXTENSIONS = {"status_report": {".txt", ".md", ".docx", ".pdf"},
              **{f: {".json", ".csv", ".xlsx"} for f in ("raid_log", "milestone_plan", "quality_summary")}}
MAX_TEXT = 100_000
MAX_FILE = 1_000_000
MAX_ROWS = 5000
MAX_COLUMNS = 80


def read_bytes(upload, field: str) -> tuple[str, str, bytes]:
    filename = Path((upload.filename or "").replace("\\", "/")).name
    extension = Path(filename).suffix.lower()
    if extension not in EXTENSIONS[field]:
        raise IngestionError(field, "extension")
    limit = MAX_TEXT if extension in {".txt", ".md"} else MAX_FILE
    data = upload.file.read(limit + 1)
    if len(data) > limit:
        raise IngestionError(field, "size")
    if not data:
        raise IngestionError(field, "empty")
    return filename, extension, data


def decode_text(data: bytes, field: str) -> str:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError:
        raise IngestionError(field, "encoding") from None
    if not text.strip():
        raise IngestionError(field, "empty")
    return text


def check_zip(data: bytes, field: str) -> None:
    if data.startswith(bytes.fromhex("d0cf11e0")):
        raise IngestionError(field, "encrypted")
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 1000 or sum(e.file_size for e in entries) > 20_000_000:
                raise IngestionError(field, "resource_limit")
            if any(e.flag_bits & 1 for e in entries):
                raise IngestionError(field, "encrypted")
            if any("vbaproject" in e.filename.lower() for e in entries):
                raise IngestionError(field, "macros")
    except BadZipFile:
        raise IngestionError(field, "malformed") from None
