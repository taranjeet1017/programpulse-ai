"""Explicit aliases and conservative conversions; unknown policy facts are not invented."""
from datetime import date, datetime
import re
from pydantic import ValidationError
from app.models.input_evidence import RaidItem, Milestone, DefectSummary, RaidLog, MilestonePlan
from .models import FileMappingResult, SourceLocation, IngestionError

COMMON = {"project": ["project name"], "reporting_date": ["reporting date", "as of date"]}
RAID = {
    "id": ["risk id", "issue id", "raid id"], "kind": ["type", "category", "raid type"],
    "title": ["description", "risk", "issue", "item"], "due_date": ["due date", "target date", "target", "resolution date"],
    "status": ["state"], "critical": ["criticality", "is critical"],
    "escalated": ["escalation", "raised to leadership"],
    "committed_resolution_date": ["committed date", "committed resolution date"],
    "material": ["is material"], "important": ["is important"], "release_blocker": ["release blocker"],
    "impact_assessed": ["impact assessed"], "affects": ["affected activities"],
    "overdue_days_reported": ["overdue days"], "evidence_key": ["evidence key"],
}
MILESTONES = {
    "id": ["milestone id", "task id"], "title": ["milestone", "milestone name", "activity", "task"],
    "baseline": ["baseline date", "planned date", "plan date"],
    "forecast": ["forecast date", "current date", "revised date"],
    "critical_path": ["critical path", "critical", "on critical path"],
    "completed": ["complete", "is complete"], "evidence_key": ["evidence key"],
}
QUALITY = {
    "planned_tests": ["planned tests", "total tests"], "executed": ["executed tests", "tests executed"],
    "passed": ["passed tests"], "failed": ["failed tests"], "blocked": ["blocked tests"],
    "sev1_open": ["sev 1 open", "severity 1 open"], "sev2_open": ["sev 2 open", "severity 2 open"],
    "sev2_reopened": ["sev 2 reopened", "reopened sev2"], "scoring_sev2": ["scoring sev2", "scoring sev 2"],
    "test_execution_percent": ["test execution percent", "execution percent"],
    "regression_testing": ["regression", "regression status"],
    "accessibility_testing": ["accessibility", "accessibility testing status"],
    "proctoring_e2e_validation": ["proctoring e2e", "e2e validation"],
}
ALIASES = {"raid_log": RAID, "milestone_plan": MILESTONES, "quality_summary": QUALITY}
MODELS = {"raid_log": RaidItem, "milestone_plan": Milestone, "quality_summary": DefectSummary}
BOOLEAN_FIELDS = {"critical", "material", "important", "escalated", "release_blocker", "impact_assessed", "critical_path", "completed"}
DATE_FIELDS = {"reporting_date", "due_date", "committed_resolution_date", "baseline", "forecast"}
NUMBER_FIELDS = set(QUALITY) - {"regression_testing", "accessibility_testing", "proctoring_e2e_validation"} | {"overdue_days_reported"}


def heading(value) -> str:
    return re.sub(r"[\s_-]+", " ", str(value or "").strip().lower())


def convert(key: str, value):
    if value is None or isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, str):
        value = value.strip()
    if key in BOOLEAN_FIELDS:
        if isinstance(value, bool):
            return value
        token = str(value).lower()
        if token in {"true", "yes", "y", "1", "critical"}:
            return True
        if token in {"false", "no", "n", "0", "not critical", "non-critical"}:
            return False
        raise ValueError("boolean")
    if key in DATE_FIELDS:
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            if not 1900 <= value.year <= 2100:
                raise ValueError("year")
            return value
        if str(value).lower() in {"tbc", "tbd", "unknown", "n/a"} and key != "baseline":
            return None
        # Deliberately reject ambiguous numeric dates and yearless dates.
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d %B %Y", "%d %b %Y"):
            try:
                parsed = datetime.strptime(str(value), fmt).date()
                if not 1900 <= parsed.year <= 2100:
                    raise ValueError("year")
                return parsed
            except ValueError:
                continue
        raise ValueError("date")
    if key in NUMBER_FIELDS:
        token = str(value).removesuffix("%")
        return float(token) if key == "test_execution_percent" else int(token) if not isinstance(value, float) else (int(value) if value.is_integer() else value)
    if key == "affects":
        return [part.strip() for part in str(value).split(";") if part.strip()]
    if key == "kind":
        return str(value).lower()
    if key in {"status", "regression_testing", "accessibility_testing", "proctoring_e2e_validation"}:
        return str(value).upper().replace("_", " ").replace("-", " ")
    return str(value)


def map_table(filename: str, field: str, worksheet: str | None, rows: list[tuple[int, list]], report):
    mapping = FileMappingResult(filename=filename, document_type=field)
    if not rows or len(rows) < 2:
        raise IngestionError(field, "empty", mapping)
    headers = [str(v or "").strip() for v in rows[0][1]]
    mapping.detected_columns = headers
    aliases = {heading(alias): key for key, names in {**COMMON, **ALIASES[field]}.items() for alias in [key, *names]}
    columns = {}
    for index, title in enumerate(headers):
        key = aliases.get(heading(title))
        if key:
            if key in columns.values():
                raise IngestionError(field, "ambiguous_columns", mapping)
            columns[index] = key
            mapping.mapped_fields[title] = key
        elif title:
            mapping.unmapped_columns.append(title)
    required = {name for name, spec in MODELS[field].model_fields.items() if spec.is_required()}
    # Metadata comes from explicit report headers; row IDs and execution percentage are derivable.
    required -= {"project", "reporting_date", "id", "test_execution_percent"}
    mapping.missing_required_fields = sorted(required - set(columns.values()))
    if mapping.missing_required_fields:
        raise IngestionError(field, "missing_columns", mapping)
    if mapping.unmapped_columns:
        mapping.warnings.append("Unrecognized columns were ignored.")
    if "project" not in columns.values() or "reporting_date" not in columns.values():
        mapping.warnings.append("Missing snapshot metadata inherited from the explicit status-report headers.")
    if field != "quality_summary" and "id" not in columns.values():
        mapping.warnings.append("Missing IDs generated from source row numbers.")
    values, locations = [], []
    for row_number, cells in rows[1:]:
        if len(cells) > len(headers) and any(v not in (None, "") for v in cells[len(headers):]):
            raise IngestionError(field, "schema", mapping)
        try:
            item = {key: convert(key, cells[i] if i < len(cells) else None) for i, key in columns.items()}
            project = item.pop("project", None) or report.project
            as_of = item.pop("reporting_date", None) or report.reporting_date
            if (project, as_of) != (report.project, report.reporting_date):
                raise IngestionError(field, "snapshot", mapping)
            if field == "quality_summary":
                item.update(project=project, reporting_date=as_of)
                if item.get("test_execution_percent") is None:
                    item["test_execution_percent"] = 100 * item["executed"] / item["planned_tests"]
            else:
                if not item.get("id"):
                    item["id"] = f"ROW-{row_number}"
                # Empty optional cells retain the model's documented defaults.
                item = {k: v for k, v in item.items() if v is not None or MODELS[field].model_fields[k].is_required()
                        or k in DATE_FIELDS}
            validated = MODELS[field].model_validate(item)
        except IngestionError:
            raise
        except (ValueError, TypeError, ZeroDivisionError, KeyError):
            raise IngestionError(field, "schema", mapping) from None
        values.append(validated)
        locations.append(SourceLocation(filename=filename, worksheet=worksheet, row=row_number,
                          columns={key: headers[i] for i, key in columns.items()}))
    try:
        if field == "quality_summary":
            if len(values) != 1:
                raise IngestionError(field, "quality_rows", mapping)
            result = values[0]
        else:
            model = RaidLog if field == "raid_log" else MilestonePlan
            result = model(project=report.project, reporting_date=report.reporting_date,
                           **{"items" if field == "raid_log" else "milestones": values})
    except ValidationError:
        raise IngestionError(field, "schema", mapping) from None
    mapping.valid = True
    mapping.warnings.append(f"{len(values)} data rows read from the first worksheet or CSV table.")
    return result, mapping, locations
