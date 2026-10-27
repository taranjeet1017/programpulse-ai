"""Conservative, deterministic date normalization; no governance decisions."""
import re
from datetime import date

from app.models.extraction import OBSERVATION_FIELDS, StatusReportExtraction

MONTHS = {name.lower(): index for index, name in enumerate((
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
), start=1)}
MONTH_PATTERN = "|".join(MONTHS)
DATES = re.compile(
    rf"\b(?:(?P<iso>\d{{4}}-\d{{2}}-\d{{2}})|"
    rf"(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<month>{MONTH_PATTERN})"
    rf"(?:\s*,?\s*(?P<year>\d{{4}}))?|"
    rf"(?P<month_first>{MONTH_PATTERN})\s+(?P<day_after>\d{{1,2}})(?:st|nd|rd|th)?"
    rf"(?:\s*,?\s*(?P<year_after>\d{{4}}))?)\b", re.I,
)
AMBIGUOUS_CONTEXT = re.compile(
    rf"\b(last|next|previous|following)\s+(year|{MONTH_PATTERN})\b"
    r"|\b(historic|historical|annually|annual|every year|either|or)\b"
    r"|\byear\s+(?:is\s+)?(?:unclear|unknown|unspecified)\b", re.I,
)
DUE_CONTEXT = re.compile(r"\b(planned|due|deadline|scheduled|target|baseline|committed|by)\b", re.I)
# A partial date is resolved only within the same calendar year and a local
# reporting window. Cross-year interpretation and distant dates stay unknown.
CONTEXT_WINDOW_DAYS = 90


def source_dates(text: str) -> list[tuple[int | None, int, int]]:
    result = []
    for match in DATES.finditer(text):
        if match["iso"]:
            year, month, day = map(int, match["iso"].split("-"))
        else:
            raw_year = match["year"] or match["year_after"]
            year = int(raw_year) if raw_year else None
            month = MONTHS[(match["month"] or match["month_first"]).lower()]
            day = int(match["day"] or match["day_after"])
        result.append((year, month, day))
    return result


def normalize_due_date(snippet: str, proposed: date | None, reporting_date: date | None) -> date | None:
    candidates = source_dates(snippet)
    if len(candidates) != 1 or (proposed is None and not DUE_CONTEXT.search(snippet)):
        return None
    year, month, day = candidates[0]
    partial = year is None
    if partial:
        if reporting_date is None or AMBIGUOUS_CONTEXT.search(snippet):
            return None
        year = reporting_date.year
    try:
        resolved = date(year, month, day)
    except ValueError:
        return None
    if not 1900 <= resolved.year <= 2100:
        return None
    if partial and abs((resolved - reporting_date).days) > CONTEXT_WINDOW_DAYS:
        return None
    return resolved


def normalize_evidence(extraction: StatusReportExtraction, report_text: str) -> StatusReportExtraction:
    normalized = extraction.model_copy(deep=True)
    context = normalized.reporting_date
    # Context must itself be explicit in the source, not merely model-generated.
    reporting_lines = re.findall(
        r"(?:reporting date|report date|status date|as of)\s*[:\-]?\s*([^\n]+)",
        report_text, re.I,
    )
    explicit_dates = {parts for line in reporting_lines for parts in source_dates(line)
                      if parts[0] is not None}
    if context is not None and explicit_dates != {(context.year, context.month, context.day)}:
        context = None
    for field in OBSERVATION_FIELDS:
        for item in getattr(normalized, field):
            item.due_date = normalize_due_date(item.source_snippet, item.due_date, context)
    return normalized
