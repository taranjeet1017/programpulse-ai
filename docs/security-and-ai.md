# Security and responsible AI

ProgramPulse is decision support, not autonomous project governance. Human leaders
remain accountable for investigating findings, reconciling sources and deciding
whether to intervene.

## Credentials and publication

API keys belong in the backend process environment or ignored root `.env`, never
in frontend variables, screenshots, examples or Git commits. Only placeholder
`.env.example` files are intended for publication. Do not upload the entire local
working directory as an archive: ignored configuration and dependencies may still
exist on disk. A clean source checkout is the publication boundary.

If a credential is ever committed, revoke/rotate it and remediate repository
history; deleting the current file alone is insufficient. No history audit can
be claimed when no Git history is available.

## Uploaded evidence and provider boundary

The application does not permanently store uploaded files or assessment history.
Uploads use bounded memory or parser-managed temporary storage and handles are
closed after processing. No uploaded content is executed. XLSM/macro-containing
Office files, encrypted documents and unsupported formats are rejected. XLSX
formulas require a values-only export; no OCR or scanned-PDF processing exists.
Resource limits and layout restrictions are documented in the
[ingestion guide](enterprise_ingestion.md).

Status-report text is sent to OpenAI during Live extraction; do not submit
confidential employer/client data without appropriate authorization and a provider
privacy review. The request uses `store=False`, which is not a claim of universal
zero retention by external infrastructure. Structured operational files are
processed locally by the assessment pipeline. API responses use `no-store` on
successful assessments; this does not control every intermediary or device.

## AI reliability and accountability

The model does not decide health. Pydantic validates structured extraction, source
quotes are checked, and dates undergo deterministic sanity checks. Management
claims remain claims, including when extraction confidence is HIGH. Structured
operational evidence controls health under explicit policy; its correctness still
requires review. No statistical calibration is implied by confidence labels.

Evidence IDs, source locations, reason details and supporting references allow
reviewers to examine why a claim was challenged. A challenge signals a need for
validation; it does not establish dishonesty or prove release failure.

## Safe failures and diagnostics

Client errors use safe messages/codes rather than raw provider bodies or stack
traces. Provider diagnostics use allowlisted fields and redact sensitive content.
Application code does not log entire uploaded documents. Protect terminal logs
and deployment infrastructure as well; application redaction is not a substitute
for organization-wide logging controls.

## Local prototype boundary

V1 has no authentication, tenancy, authorization, durable retention policy or
billing quota. Explicit localhost CORS is a browser restriction, not access control.
Use loopback binding for local demonstrations. Do not expose this service publicly
as a production upload endpoint without additional controls and adversarial review.
Schema validation and quote checks reduce risk but do not eliminate prompt
injection, semantic extraction errors or malicious-file resource exhaustion.

## Synthetic demonstration data

The AssessPro scenario and all associated project evidence are synthetic and created solely for demonstration purposes.

Use those files for interviews, screenshots and automated validation. Do not
replace them with confidential data in a public repository.
