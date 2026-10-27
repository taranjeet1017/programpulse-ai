# API and diagnostics reference

Start the backend and visit `/docs` for generated schemas. Routes retained in V1:

- `GET /health`: service health, no provider call.
- `GET /api/v1/demo-assessment`: deterministic local assessment, no provider call;
  compatibility schema uses `assessed_health` and `health_dimensions`.
- `POST /api/v1/ai/extract-status-report`: JSON `text`, returns typed extraction.
- `GET /api/v1/demo-ai-extraction`: extraction plus provider token usage.
- `GET /api/v1/demo-ai-assessment`: detailed audit assessment including full catalog.
- `GET /api/v1/demo-ai-assessment/summary`: compact dashboard assessment.
- `POST /api/v1/ai/assess-files`: four required multipart files; compact dashboard assessment.

Each valid AI route request performs one extraction. Calling multiple routes is
not reuse of an earlier result. The summary projection itself is pure and makes no
provider request when supplied an already completed assessment.

## Uploaded assessment

Fields: `status_report`, `raid_log`, `milestone_plan`, `quality_summary`. Use the
[ingestion guide](enterprise_ingestion.md) for limits, schemas, aliases and metadata.
From the repository root, this explicit command incurs one extraction request:

```bash
curl --fail-with-body http://127.0.0.1:8000/api/v1/ai/assess-files \
  -F 'status_report=@sample_data/assesspro_enterprise/weekly_status_report.docx' \
  -F 'raid_log=@sample_data/assesspro_enterprise/raid_log.xlsx' \
  -F 'milestone_plan=@sample_data/assesspro_enterprise/milestone_plan.xlsx' \
  -F 'quality_summary=@sample_data/assesspro_enterprise/defect_summary.xlsx'
```

## Response boundaries

The compact contract includes project, reporting snapshot date, assessment version,
reported and ProgramPulse health, conflict, confidence, leadership attention,
six dimension summaries, challenges, actions, executive summary and key evidence.
It excludes the complete catalog, event groups and token usage. Its date is the
source reporting date, not the request execution date.

The detailed demo contract retains the full catalog and compatibility aliases.
Dimension reasons have `reason_details` tying individual reasons to evidence IDs,
alongside legacy reason/ID lists. The compact shortlist may omit an ID referenced
by a challenge; use detailed audit context when available rather than treating the
shortlist as a complete evidence set. No separate persisted upload-audit endpoint exists.

## Errors and diagnostics

- 422: missing/invalid input, file, schema or mapping.
- 413: multipart body exceeds its limit.
- 503: missing configuration or unavailable required resources.
- 502: provider failure, refusal, incomplete/invalid extraction or invalid output.
- 504: provider timeout.

The server terminal logs a JSON `openai_extraction_failure` event with category,
exception class, configured model, safe message, HTTP/provider codes and request
ID when available. Sensitive diagnostics are suppressed. Swagger shows the HTTP
contract; inspect the server terminal for safe diagnostic detail. Do not paste
credentials or unreviewed logs into issues.

The provider client has a 60-second timeout, no automatic retries and a 12,000
output-token limit. The browser stops waiting after 90 seconds without guaranteeing
cancellation upstream. Fix the cause and explicitly rerun when appropriate.
