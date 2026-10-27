"""File orchestration, before the paid extraction boundary."""
import json
from dataclasses import dataclass
from pydantic import ValidationError
from app.models.extraction import StatusReportRequest
from app.models.input_evidence import DefectSummary, MilestonePlan, ProjectEvidence, RaidLog
from app.services.sample_loader import parse_status_report
from .models import IngestionError, FileMappingResult, SourceLocation, StatusReportDocument
from .safety import read_bytes, decode_text
from .document_reader import read_document
from .csv_reader import read_csv
from .spreadsheet_reader import read_xlsx
from .field_mapper import map_table

CANONICAL = {"status_report": "weekly_status_report.md", "raid_log": "raid_log.json",
             "milestone_plan": "milestone_plan.json", "quality_summary": "defect_summary.json"}

@dataclass
class IngestedEvidence:
    bundle: ProjectEvidence
    document: StatusReportDocument
    mappings: list[FileMappingResult]
    names: dict[str, str]
    locations: dict[str, SourceLocation]


def ingest_uploads(uploads) -> IngestedEvidence:
    raw = {field: read_bytes(upload, field) for field, upload in uploads.items()}
    doc = read_document(*raw["status_report"])
    try:
        StatusReportRequest(text=doc.extracted_text)
        report = parse_status_report(doc.extracted_text)
    except ValueError:
        raise IngestionError("status_report", "metadata") from None
    sources, mappings, locations = {}, [], {}
    for field, model in (("raid_log", RaidLog), ("milestone_plan", MilestonePlan), ("quality_summary", DefectSummary)):
        filename, ext, data = raw[field]
        if ext == ".json":
            try:
                value = json.loads(decode_text(data, field))
            except (ValueError, RecursionError) as exc:
                if isinstance(exc, IngestionError):
                    raise
                raise IngestionError(field, "json") from None
            try:
                source = model.model_validate(value)
            except ValidationError:
                raise IngestionError(field, "schema") from None
            mapping = FileMappingResult(filename=filename, document_type=field, valid=True)
        else:
            sheet, rows = read_xlsx(data, field) if ext == ".xlsx" else read_csv(data, field)
            source, mapping, row_locations = map_table(filename, field, sheet, rows, report)
            for index, location in enumerate(row_locations):
                suffix = f"#/items/{index}" if field == "raid_log" else f"#/milestones/{index}" if field == "milestone_plan" else ""
                locations[CANONICAL[field] + suffix] = location
        if (source.project, source.reporting_date) != (report.project, report.reporting_date):
            raise IngestionError(field, "snapshot", mapping)
        sources[field] = source
        mappings.append(mapping)
    return IngestedEvidence(
        bundle=ProjectEvidence(weekly_status=report, raid=sources["raid_log"],
                               milestone_plan=sources["milestone_plan"], quality=sources["quality_summary"]),
        document=doc, mappings=mappings,
        names={CANONICAL[field]: values[0] for field, values in raw.items()}, locations=locations,
    )
