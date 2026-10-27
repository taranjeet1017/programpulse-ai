# ProgramPulse AI technical and product case study

## Problem

Delivery leaders need to judge whether reported project health is supported by
execution evidence. The evidence often sits in separate reports, RAID registers,
milestone plans and quality summaries, leaving reconciliation to periodic meetings.

## Why existing project reporting is insufficient

A RAG label compresses a complex situation into one assertion. A report can state
that development is on track while a critical dependency lacks a recovery date,
regression has not started and downstream dates remain unchanged. Summarizing the
report alone preserves that framing instead of examining it.

## Product hypothesis

An independent assurance layer can make leadership review more useful by comparing
management statements with operational facts, exposing contradictions and recommending
specific interventions with traceable support. V1 tests the technical feasibility
of this workflow; it does not establish improved business outcomes or predictive accuracy.

## Design decisions

The system separates interpretation from decision policy, requires a complete
four-source snapshot, and retains claims rather than rewriting them as facts.
The dashboard makes reported-versus-assessed health the central comparison. Cost
and error handling are part of the workflow, with a free sample and explicit submission.
See [design decisions](design-decisions.md) for tradeoffs.

## Architecture

FastAPI delegates document reading to dedicated ingestion modules. Narrative text
passes through one structured OpenAI extraction. Operational sources use deterministic
parsers and Pydantic validation. Canonical adapters, event consolidation and rules
produce health, challenges and actions. A compact projection populates the Next.js
dashboard. The [architecture diagram](architecture.md) shows both evidence branches.

## Why AI is used only for evidence interpretation

Reports express claims, observations and omissions in prose. AI helps extract those
into a typed representation while retaining source snippets. Schema and quote
validation constrain the result, but cannot establish that a claim is true. Keeping
AI at this boundary limits the scope of variability and makes downstream reasoning inspectable.

## Why deterministic rules are used for governance decisioning

Leadership needs to understand which policy fired and why. Explicit rules permit
threshold testing, recovery-to-GREEN tests and release-blocker handling without
asking a language model to invent a risk score. The tradeoff is deliberate: rule
coverage is finite and requires calibration to an organization's governance standards.

## AssessPro demo scenario

The AssessPro scenario and all associated project evidence are synthetic and created solely for demonstration purposes.

AssessPro Modernization & Feature Expansion has a reporting date of 18 September
2026 and a target release of 30 November 2026. Management reports GREEN.
ProgramPulse calculates AMBER, with Dependencies RED and five AMBER dimensions.
This indicates material exposure requiring intervention; it is not a prediction
that the release must fail.

## Evidence that drove the challenge

Proctoring certification was due on 9 September and remains pending without a
revised committed date, affecting end-to-end testing and UAT readiness. Eleven
Sev-2 defects remain open, three have reopened, and regression/accessibility
validation is incomplete. Critical-path milestones have slipped while UAT remains
fixed. Material reporting scope changes lack an impact assessment, and important
actions are overdue without appropriate escalation.

The narrative describes all 11 Sev-2 defects as scoring defects; the quality
snapshot records six scoring defects among 11 total. The system preserves this
classification discrepancy for reconciliation rather than silently resolving it.
Reporting Development is explicitly not a critical-path milestone.

## Governance interventions produced

The assessment challenges broad on-track/no-impact positions and the assertion
that escalation is unnecessary. It also identifies the defect classification
conflict. Equivalent challenges consolidate while retaining supporting evidence.
Recommended actions include obtaining dependency recovery commitments, reforecasting
the critical path and validating UAT readiness, requiring a defect recovery and
regression plan, completing scope impact assessment, and assigning recovery owners/dates.

## Engineering approach

Typed contracts separate API transport, ingestion, provider interaction and governance
logic. Legacy endpoints remain compatible. Evidence is normalized before rules,
and full audit output is separated from a small dashboard projection. No persistence,
connectors or agent framework were added merely to make the prototype appear larger.

## Testing approach

Tests exercise source validation, rule boundaries, event association, claim
consolidation, reason-level traceability and safe provider failures. Frontend tests
cover zero-request sample loading, one explicit submission, pending states,
retained selections/results and reset behavior. Provider calls are mocked and real
HTTP transport is blocked in backend tests. [Validation](validation.md) records
actual results rather than presenting test count as proof of production readiness.

## Enterprise document ingestion

Equivalent DOCX/XLSX and TXT/JSON AssessPro bundles produce materially equivalent
health, governance conclusions and actions under mocked extraction. XLSX/CSV aliases
are transparent, dates and booleans convert deterministically, and evidence retains
original worksheet rows. Text-based PDF support excludes OCR. The format contract
is intentionally narrower than arbitrary enterprise document understanding.

## Cost control approach

The sample is local and free of provider usage. Each valid Live assessment performs
one extraction; all later processing is deterministic. Input validation precedes
that call, and neither the UI nor SDK automatically retries. These choices make
cost behavior understandable but do not replace authentication or usage controls.

## What V1 proves

V1 demonstrates an end-to-end path from enterprise-format evidence to a traceable
independent health assessment and leadership-facing UI. The project owner reports
successful manual enterprise-format validation. Automated equivalence tests provide
repeatable checks with mocked extraction. No measured ROI, accuracy benchmark,
customer deployment or real-world delivery improvement is claimed.

## Future evolution

Potential next steps include project-system connectors, configurable policies,
historical trajectories and role-based review workflows. Production adoption would
also require privacy/retention design, authentication, rate limits, deployment
hardening and evaluation against representative organizational evidence. Specialized
delivery agents remain a possible direction, not a current capability.
