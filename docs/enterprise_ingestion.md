# Enterprise evidence formats

Recommended input: DOCX for weekly status and XLSX for RAID, milestones and quality.
TXT/MD and JSON remain compatible. PDFs must contain embedded selectable text;
scanned PDFs are rejected without OCR. UTF-8 CSV is supported with comma delimiters.

All four files are required. The status report still needs explicit Project,
Reporting date, Reported overall health and Target production release headers,
as ordinary paragraphs or a two-column Word table. This avoids asking AI to invent
snapshot metadata. Dates in those headers use YYYY-MM-DD.

## Spreadsheet layout and conversions

Use the first worksheet, with headings on the first nonblank row and data below.
Blank rows are skipped; original worksheet row numbers remain in provenance.
CSV row numbers are logical records, including the heading and blank records.
No merged header groups, pivot layouts, key/value quality sheets or individual
raw-defect lists are interpreted. Quality uses exactly one wide metrics row.

Heading matching trims whitespace, ignores case, and treats spaces, underscores
and hyphens equivalently. Unknown columns are ignored and recorded in mapping
warnings. Duplicate aliases mapping to one field are rejected, not guessed.

Project/reporting-date columns are optional; absent values inherit the explicit
report headers with a mapping warning. Supplied values must agree with the report.
Absent IDs are generated as ROW-<original row number>. Blank optional fields retain
the existing model defaults: critical=false, impact_assessed=true, affects=[] and
nullable dates/keys. Required boolean policy fields are never inferred from prose.
The quality execution percentage can be derived from executed/planned counts;
if supplied it uses 0–100 units, optionally with a trailing % sign.

Dates accept real Excel date cells, YYYY-MM-DD, YYYY/MM/DD, or day + English month
name + four-digit year. Ambiguous slash dates and missing years are rejected.
TBC/TBD/unknown/N/A mean an unknown nullable date; a baseline must be known.
Booleans accept Yes/No, True/False, Y/N, 1/0; critical/not critical/non-critical
are also recognized. Status strings normalize case, underscores and hyphens.
Affects is a semicolon-separated list. Counts must be nonnegative integers and
quality totals must reconcile according to the existing Pydantic schema.

XLSX formulas are not evaluated or trusted: export values before uploading.
Only .xlsx is accepted; .xls, .xlsm and macro-containing archives are rejected.

## Recognized columns

Every canonical field name below is accepted in addition to its aliases.

### Raid Log

Required columns: `kind`, `title`, `status`, `material`, `important`, `escalated`, `release_blocker`.

- `project`: `project name`.
- `reporting_date`: `reporting date`, `as of date`.
- `id`: `risk id`, `issue id`, `raid id`.
- `kind`: `type`, `category`, `raid type`.
- `title`: `description`, `risk`, `issue`, `item`.
- `due_date`: `due date`, `target date`, `target`, `resolution date`.
- `status`: `state`.
- `critical`: `criticality`, `is critical`.
- `escalated`: `escalation`, `raised to leadership`.
- `committed_resolution_date`: `committed date`, `committed resolution date`.
- `material`: `is material`.
- `important`: `is important`.
- `release_blocker`: `release blocker`.
- `impact_assessed`: `impact assessed`.
- `affects`: `affected activities`.
- `overdue_days_reported`: `overdue days`.
- `evidence_key`: `evidence key`.

### Milestone Plan

Required columns: `title`, `baseline`, `forecast`, `critical_path`, `completed`.

- `project`: `project name`.
- `reporting_date`: `reporting date`, `as of date`.
- `id`: `milestone id`, `task id`.
- `title`: `milestone`, `milestone name`, `activity`, `task`.
- `baseline`: `baseline date`, `planned date`, `plan date`.
- `forecast`: `forecast date`, `current date`, `revised date`.
- `critical_path`: `critical path`, `critical`, `on critical path`.
- `completed`: `complete`, `is complete`.
- `evidence_key`: `evidence key`.

### Quality Summary

Required columns: `planned_tests`, `executed`, `passed`, `failed`, `blocked`, `sev1_open`, `sev2_open`, `sev2_reopened`, `scoring_sev2`, `regression_testing`, `accessibility_testing`, `proctoring_e2e_validation`.

- `project`: `project name`.
- `reporting_date`: `reporting date`, `as of date`.
- `planned_tests`: `planned tests`, `total tests`.
- `executed`: `executed tests`, `tests executed`.
- `passed`: `passed tests`.
- `failed`: `failed tests`.
- `blocked`: `blocked tests`.
- `sev1_open`: `sev 1 open`, `severity 1 open`.
- `sev2_open`: `sev 2 open`, `severity 2 open`.
- `sev2_reopened`: `sev 2 reopened`, `reopened sev2`.
- `scoring_sev2`: `scoring sev2`, `scoring sev 2`.
- `test_execution_percent`: `test execution percent`, `execution percent`.
- `regression_testing`: `regression`, `regression status`.
- `accessibility_testing`: `accessibility`, `accessibility testing status`.
- `proctoring_e2e_validation`: `proctoring e2e`, `e2e validation`.

## Diagnostics and provenance

`StatusReportDocument` records filename, type, extracted text, character count,
PDF page count, warnings and metadata. DOCX reads body paragraphs and tables in
order; headers, footers, drawings and text boxes are not included. PDF text order
can differ from visual order. Neither reader recreates formatting.

`FileMappingResult` is produced internally before assessment, with detected,
mapped and unmapped columns, missing fields, warnings and validity. This is not
a field-mapping UI and does not change the dashboard response contract. Safe 422
responses identify the file, reason and canonical missing fields when relevant.
No parser exception strings or document contents are returned in errors.

Structured evidence carries original filename, worksheet and row in its source
reference and section. The detailed normalized record also retains canonical-to-
original column mapping. Narrative evidence retains filename, extracted section
and verified snippet. Extraction indices are logical references, not fabricated
Word page or PDF coordinates. JSON pointer provenance remains compatible.

## Limits and processing

Binary documents and structured files: 1,000,000 bytes per file. TXT/MD reports:
100,000 bytes. Total multipart body: 3,200,000 bytes including form overhead.
Extracted status text: 100,000 characters. Office archives: at most 1,000 entries
and 20 MB declared expanded size. Sheets: 5,000 data rows and 80 columns. PDFs:
50 pages and up to 2 MB decoded page content per page. Files exceeding these
limits, encrypted or malformed files, and PDFs with fewer than 40 alphanumeric
extracted characters are rejected. No OCR, macro execution or persistent storage.

All ingestion and Pydantic validation finish before the one AI extraction request.
Health remains entirely determined by the existing governance rules. Sample mode
costs nothing; every successful uploaded/live submission consumes one extraction.
