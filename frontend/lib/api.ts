import { DIMENSIONS, type DashboardAssessment } from "./types";

// Single public URL configuration. API keys must never enter this application.
export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
export const SUMMARY_PATH = "/api/v1/demo-ai-assessment/summary";
const string = (value: unknown): value is string => typeof value === "string";
const record = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(string);
const nullableString = (value: unknown) => value === null || string(value);
const status = (value: unknown) => value === "GREEN" || value === "AMBER" || value === "RED";
const dimension = (value: unknown) => DIMENSIONS.some((name) => name === value);

// Validate the render-critical wire contract without a schema-library dependency.
export function isDashboardAssessment(value: unknown): value is DashboardAssessment {
  if (!record(value)) return false;
  return string(value.project) && string(value.assessment_version) && string(value.assessment_date)
    && /^\d{4}-\d{2}-\d{2}$/.test(value.assessment_date) && Number.isFinite(Date.parse(value.assessment_date))
    && status(value.reported_health) && status(value.programpulse_health)
    && ["LOW", "MEDIUM", "HIGH"].some((confidence) => confidence === value.confidence)
    && typeof value.status_conflict === "boolean" && typeof value.leadership_attention_required === "boolean"
    && string(value.executive_summary)
    && Array.isArray(value.dimension_summary) && value.dimension_summary.length === DIMENSIONS.length
    && new Set(value.dimension_summary.map((item: unknown) => record(item) ? item.dimension : null)).size === DIMENSIONS.length
    && value.dimension_summary.every((item: unknown) => record(item) && dimension(item.dimension) && status(item.status)
      && string(item.headline_reason) && typeof item.evidence_count === "number" && Number.isInteger(item.evidence_count) && item.evidence_count >= 0)
    && Array.isArray(value.top_governance_challenges) && value.top_governance_challenges.every((item: unknown) => record(item)
      && string(item.challenge_id) && string(item.reported_claim) && string(item.reason)
      && (item.assessment === "CHALLENGED" || item.assessment === "REQUIRES_VALIDATION")
      && (item.severity === "AMBER" || item.severity === "RED") && strings(item.supporting_evidence_ids) && strings(item.claim_evidence_ids))
    && Array.isArray(value.top_recommended_actions) && value.top_recommended_actions.every((item: unknown) => record(item)
      && string(item.action_id) && string(item.description) && strings(item.supporting_evidence_ids))
    && Array.isArray(value.key_evidence) && value.key_evidence.every((item: unknown) => record(item)
      && string(item.evidence_id) && string(item.description) && string(item.evidence_kind)
      && string(item.source_type) && string(item.source_name) && string(item.source_reference)
      && nullableString(item.source_section) && nullableString(item.source_snippet)
      && Array.isArray(item.dimensions) && item.dimensions.every(dimension));
}

export class AssessmentRequestError extends Error {}

export async function runLiveAssessment(signal: AbortSignal): Promise<DashboardAssessment> {
  // Deliberately one fetch: no polling, prefetching, refresh or automatic retry.
  const response = await fetch(`${API_BASE_URL}${SUMMARY_PATH}`, {
    method: "GET", cache: "no-store", credentials: "omit", signal,
  });
  if (!response.ok) {
    // Never display backend/provider response bodies or diagnostics in the UI.
    if (response.status === 503) throw new AssessmentRequestError("Live assessment is unavailable. Check the backend configuration before trying again.");
    if (response.status === 504) throw new AssessmentRequestError("The assessment timed out. Your current assessment has been retained.");
    throw new AssessmentRequestError("The live assessment could not be completed. Your current assessment has been retained.");
  }
  const data: unknown = await response.json();
  if (!isDashboardAssessment(data)) throw new AssessmentRequestError("The assessment response could not be validated. Your current assessment has been retained.");
  return data;
}
