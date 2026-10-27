# V1 validation and publication review

Validation date: **26 October 2026**. No paid provider request was made for this review.

## Actual automated results

- Backend: **196 tests passed** (`python -m pytest -q`, from `backend/`).
- Frontend: **38 tests passed**, three Vitest files (`npm test`).
- ESLint: passed (`npm run lint`).
- TypeScript: passed (`npm run typecheck`, after build).
- Production build: passed (`npm run build`, Next.js 16.4.2 with webpack).
  The dashboard route is statically prerendered; Live submission happens later.

The checks used the existing Python 3.14 virtual environment and Node.js 24.19.0.
Python 3.11+ is the declared minimum, not a claim that every supported version was
tested. These are local checks, not CI matrix, load-test or deployment certification.

## Enterprise-format validation

Tests cover DOCX body/table extraction, embedded PDF text, XLSX/CSV parsing, aliases,
date/boolean conversion, blank rows, missing fields, source rows, malformed files,
size limits and formula rejection. Equivalent TXT/JSON and DOCX/XLSX bundles
return reported GREEN, ProgramPulse AMBER, Dependencies RED and status conflict.
Comparison tests verify six-dimension statuses, governance challenge reasons and
core recommended actions.

Extraction is mocked in those comparisons: they prove deterministic cross-format
consistency given an extraction fixture, not identical live model behavior. The
project owner reports successful manual enterprise-format validation before this
review. No new live run, live screenshot or independent provider transcript was
produced during this publication pass.

## No-paid-call test approach

Backend autouse fixtures isolate environment configuration and block real HTTPX
transport. Tests mock extraction or provider responses. Frontend tests mock fetch,
including zero-request Sample mode, explicit single submissions, safe errors,
retained results/selections and reset behavior. No real API credential is required.

## Publication safety review

Candidate source files and the XML/relationship contents of all four Office
archives were scanned for actual local secret values, common credential/private-key
patterns and machine-specific paths. No actionable matches were found. Short fake
credentials remain deliberately in redaction tests; they are not real secrets.
The AssessPro data is synthetic. This bounded review is not a guarantee that an
automated scanner detects every possible secret or establishes data ownership.

The root `.env` remains local and ignored. A temporary Git repository verified
ignore coverage for env files, virtual environments, Python/Next caches,
node_modules, IDE files, uploads and test artifacts. Example env files and intended
screenshots remain includable. No Git repository/history exists in the project
directory, so no staged index or prior commits could be audited. Nothing was published.

Before publication, inspect `git status` and `git diff --cached`. Stage intended
source only; never force-add ignored secrets or upload an archive of the entire
local working directory. Enable repository secret scanning where available.
MIT licensing is included; dependencies retain their own licenses.

## Cleanup and remaining warnings

The chronological README and stale architecture/product statements were replaced
with current V1 documentation. Compatibility routes remain intact. Two unused
API size constants were removed; ingestion owns per-file limits. Disposable OS
metadata was removed. Runtime dependencies and active build output remain local
and ignored, rather than being deleted from a working environment.

One existing Starlette warning concerns deprecated HTTPX TestClient integration;
it does not fail tests. No dependencies were changed merely to suppress it.
Screenshots are capture instructions only; a genuine Live screenshot remains an
optional manual task requiring an explicitly authorized provider request.

The reviewed source is prepared for public GitHub publication after normal staging
review. The running application is still a local prototype without authentication,
production security review, calibrated governance policies or deployment hardening.
