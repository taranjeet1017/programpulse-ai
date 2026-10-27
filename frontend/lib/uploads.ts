import { API_BASE_URL, AssessmentRequestError, isDashboardAssessment } from "./api";
import type { DashboardAssessment } from "./types";

export const FILE_FIELDS = [
  { key: "status_report", label: "Weekly Status Report", accept: ".docx,.pdf,.txt,.md", help: "Word, PDF or text document", limit: 1_000_000 },
  { key: "raid_log", label: "RAID Log", accept: ".xlsx,.csv,.json", help: "Excel, CSV or JSON file", limit: 1_000_000 },
  { key: "milestone_plan", label: "Milestone Plan", accept: ".xlsx,.csv,.json", help: "Excel, CSV or JSON file", limit: 1_000_000 },
  { key: "quality_summary", label: "Quality / Defect Summary", accept: ".xlsx,.csv,.json", help: "Excel, CSV or JSON file", limit: 1_000_000 },
] as const;
export type FileField = typeof FILE_FIELDS[number]["key"];
export type EvidenceFiles = Partial<Record<FileField, File>>;
export type FileErrors = Partial<Record<FileField, string>>;
const reasons: Record<string, string> = {
  extension: "has an unsupported file extension.", empty: "is empty.",
  size: "exceeds the file-size limit.", encoding: "must use UTF-8 text encoding.",
  json: "is not valid JSON.", schema: "does not match the expected structure.",
  metadata: "requires valid Project, Reporting date, Reported overall health and Target production release headers.",
  pdf_text: "contains insufficient machine-readable text. Scanned PDFs are not supported.",
  encrypted: "is password-protected or encrypted and is not supported.",
  malformed: "could not be read. Check that the file is valid and not encrypted.",
  resource_limit: "exceeds the supported document complexity limits.",
  macros: "contains unsupported macros.", formulas: "contains formulas. Export values before uploading.",
  missing_columns: "is missing required recognizable columns. Check the supplied template.",
  ambiguous_columns: "has multiple columns mapping to the same field.",
  quality_rows: "must contain exactly one summary metrics row.",
  snapshot: "must match the report's project and reporting date.",
};
export function validateFile(field: FileField, file: File): string | undefined {
  const spec = FILE_FIELDS.find(item => item.key === field)!;
  const extension = `.${file.name.split(".").pop()?.toLowerCase()}`;
  if (!(spec.accept as string).split(",").includes(extension)) return `${spec.label} ${reasons.extension}`;
  if (!file.size) return `${spec.label} ${reasons.empty}`;
  if (file.size > ([".txt", ".md"].includes(extension) ? 100_000 : spec.limit)) return `${spec.label} ${reasons.size}`;
}
export class UploadRequestError extends AssessmentRequestError {
  constructor(message: string, public fields: FileErrors = {}) { super(message); }
}
export async function assessFiles(files: EvidenceFiles, signal: AbortSignal): Promise<DashboardAssessment> {
  const form = new FormData();
  for (const {key} of FILE_FIELDS) {
    const file = files[key];
    if (!file || validateFile(key, file)) throw new UploadRequestError("Check all four required files.");
    form.append(key, file);
  }
  const response = await fetch(`${API_BASE_URL}/api/v1/ai/assess-files`, {
    method: "POST", body: form, signal, cache: "no-store", credentials: "omit",
  });
  if (!response.ok) {
    if (response.status === 422) {
      const body: unknown = await response.json().catch(() => null);
      // Only translate a closed vocabulary; never render server-provided messages.
      if (body && typeof body === "object" && "detail" in body) {
        const detail = body.detail;
        if (detail && typeof detail === "object" && "field" in detail && "reason" in detail) {
          const spec = FILE_FIELDS.find(item => item.key === detail.field);
          if (spec && typeof detail.reason === "string" && Object.hasOwn(reasons, detail.reason)) {
            const knownFields = ["title", "kind", "status", "material", "important", "escalated", "release_blocker", "baseline", "forecast", "critical_path", "completed", "planned_tests", "executed", "passed", "failed", "blocked", "sev1_open", "sev2_open", "sev2_reopened", "scoring_sev2", "regression_testing", "accessibility_testing", "proctoring_e2e_validation"];
            const missing = "missing_required_fields" in detail && Array.isArray(detail.missing_required_fields)
              ? detail.missing_required_fields.filter((field: unknown): field is string => typeof field === "string" && knownFields.includes(field)) : [];
            const suffix = missing.length ? ` Required: ${missing.map(field => field.replaceAll("_", " ")).join(", ")}.` : "";
            throw new UploadRequestError("Please correct the highlighted file.", { [spec.key]: `${spec.label} ${reasons[detail.reason]}${suffix}` });
          }
        }
      }
      throw new UploadRequestError("All four files are required and must match the expected structure.");
    }
    if (response.status === 413) throw new UploadRequestError("The upload is too large. Keep the combined upload below 3.2 MB, each file below 1 MB and plain-text reports below 100 KB.");
    if (response.status === 503) throw new UploadRequestError("Assessment is unavailable. Check the backend AI configuration.");
    if (response.status === 504) throw new UploadRequestError("The assessment timed out. Your files are retained; no retry was made.");
    throw new UploadRequestError("The assessment could not be completed. Your files are retained; no retry was made.");
  }
  const data: unknown = await response.json();
  if (!isDashboardAssessment(data)) throw new UploadRequestError("The assessment response could not be validated. Your files are retained.");
  return data;
}
