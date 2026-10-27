"""Typed ingestion diagnostics and original source locations."""
from typing import Any
from pydantic import BaseModel, Field


class StatusReportDocument(BaseModel):
    filename: str
    file_type: str
    extracted_text: str
    character_count: int
    page_count: int | None = None
    warnings: list[str] = Field(default_factory=list)
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class FileMappingResult(BaseModel):
    filename: str
    document_type: str
    detected_columns: list[str] = Field(default_factory=list)
    mapped_fields: dict[str, str] = Field(default_factory=dict)
    unmapped_columns: list[str] = Field(default_factory=list)
    missing_required_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    valid: bool = False


class SourceLocation(BaseModel):
    filename: str
    worksheet: str | None = None
    row: int | None = None
    columns: dict[str, str] = Field(default_factory=dict)

    def reference(self) -> str:
        parts = ([f"Sheet: {self.worksheet}"] if self.worksheet else [])
        if self.row is not None:
            parts.append(f"Row: {self.row}")
        return self.filename + (" | " + " | ".join(parts) if parts else "")


class IngestionError(ValueError):
    def __init__(self, field: str, reason: str, mapping: FileMappingResult | None = None):
        self.field, self.reason, self.mapping = field, reason, mapping
        super().__init__(reason)
