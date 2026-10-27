# Interview demo script

Target duration: 4–5 minutes. Use synthetic AssessPro files only. Start both servers,
check `/health`, and verify account/model configuration privately before a planned
Live demonstration. Never show the key. A real run incurs one extraction request.
Keep the Sample view available if the provider is unavailable; clearly identify
it as Sample rather than disguising a fallback as Live.

## 0:00–0:40 — The problem

“AssessPro is reported GREEN. That is management's position, but supporting facts
are spread across the report, dependency register, milestone plan and quality
snapshot. ProgramPulse asks whether those sources support the reported confidence.”

Show the sample comparison briefly, making its sample label clear.

## 0:40–1:20 — Upload evidence

Open Analyze Project Evidence. Select the DOCX report and three XLSX files in
`sample_data/assesspro_enterprise/`. Explain the four evidence roles and show their
validation states. “Selection doesn't run AI. The application validates the files
and maps operational fields deterministically before requesting extraction.”

## 1:20–2:00 — Run assessment

Point out the cost note and click Run Assessment once. While the real progress
state is displayed, explain: “One model call extracts the narrative. It does not
choose the health rating. The rules evaluate operational facts independently.”
Do not promise a fixed completion time. If the request fails, explain the safe
error and retained files, then explicitly switch to Sample for the remaining tour.

## 2:00–2:45 — Show the disagreement

After success, show LIVE and the project name. “Reported GREEN becomes AMBER.
Dependencies is RED because certification is overdue without a committed recovery
date. Quality remediation and critical-path compression add exposure. That does
not prove the release must fail; it establishes the need for leadership attention.”

## 2:45–3:35 — Challenge a claim

Expand “No release impact is currently anticipated.” Show the reason and evidence
IDs/source references. “The system preserves the claim and shows the facts that
challenge it. For spreadsheet evidence, reviewers can return to the original
worksheet and row. Repeated mentions aren't counted as extra risks.”

Point out the separate scoring-defect classification discrepancy if time permits.
Do not imply that every audit reference is present in the compact evidence shortlist.

## 3:35–4:15 — Leadership intervention

Show the recommended actions: obtain owned certification recovery commitments,
reforecast the critical path and validate UAT readiness, then require a defect
recovery/regression plan. “The output is an agenda for decisions and commitments,
with evidence behind each action. Accountability stays with the delivery leaders.”

## 4:15–4:50 — Architecture and scope

“AI interprets evidence; governance rules make the health determination. The
pipeline is typed, traceable and covered by offline tests, including equivalent
JSON and enterprise-format scenarios. V1 proves the workflow, not predictive
accuracy or production readiness. Organizational policy calibration, authenticated
integrations and historical evaluation would be the next practical investments.”
