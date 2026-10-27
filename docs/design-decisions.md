# Design decisions

These decisions describe implemented V1 behavior and its tradeoffs.

## One extraction call per assessment

Each valid Live request makes one structured extraction call. Normalization,
health, challenges, recommendations and summary generation are deterministic.
This bounds provider use and makes failures easier to diagnose. It does not provide
cross-request caching: repeated runs cost again.

## No LLM health scoring

The LLM interprets the report; it cannot assign final RAG health or override
operational policy facts. Rules are inspectable and testable, at the cost of a
narrower, explicitly maintained policy set requiring organizational calibration.

## Pydantic structured outputs

Extraction and API responses use typed schemas. Provider output must parse and
quoted snippets must occur in the source. This improves structural reliability
without proving semantic accuracy or truth.

## Deterministic normalization and consolidation

Partial dates are resolved conservatively; implausible dates are rejected or
normalized from supported context. Stable event keys associate related evidence
without deleting distinct source records or inflating risk through repeated mentions.
Ambiguous associations remain separate rather than being guessed by another model.

## Claims retained and operational precedence explicit

A high-confidence extraction of a claim does not make the claim true. Management
statements remain visible alongside contradictory findings. Validated structured
operational evidence controls health, while disagreements support challenges and
human source reconciliation. Structured systems may also be wrong.

## Provenance at each decision boundary

Reasons, challenges and actions reference evidence. Original filenames, excerpts,
JSON pointers or worksheet rows remain traceable. The compact dashboard intentionally
omits the full catalog, so a shortlist cannot resolve every audit reference inline.

## Explicit document contracts

DOCX/PDF provide narrative text. XLSX/CSV columns map through documented aliases;
JSON remains compatible. No AI mapping, OCR or formula execution is introduced.
This makes conversions reproducible but requires predictable headers and schemas.

## No vector database or orchestration framework

V1 evaluates a bounded four-file snapshot. It needs neither retrieval ranking nor
LangChain/LlamaIndex to coordinate a single extraction and ordinary Python services.
Additional infrastructure would not establish better governance evidence by itself.

## No persistence in V1

Uploaded files and assessment results are not permanently stored by the application.
This keeps the workflow focused and avoids an undeveloped retention model. Users
cannot recover prior assessments or compare historical trajectories.

## Sample and Live modes with cost controls

Sample mode uses a local typed fixture and never calls the backend. Live submission
requires an explicit click, disables duplicate pending submissions and does not
retry automatically. Failure preserves the previous result or file selections.
The UI describes cost before submission; these controls are not billing quotas
or authentication. Browser cancellation may leave a server request running.
