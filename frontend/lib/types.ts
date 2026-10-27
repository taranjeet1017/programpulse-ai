export type HealthStatus = "GREEN" | "AMBER" | "RED";
export type Confidence = "LOW" | "MEDIUM" | "HIGH";
export const DIMENSIONS = ["SCHEDULE", "SCOPE", "QUALITY", "DEPENDENCIES", "ACTIONS", "GOVERNANCE"] as const;
export type Dimension = (typeof DIMENSIONS)[number];
export interface DimensionSummary {
  dimension: Dimension;
  status: HealthStatus;
  headline_reason: string;
  evidence_count: number;
}
export interface GovernanceChallenge {
  challenge_id: string;
  reported_claim: string;
  assessment: "CHALLENGED" | "REQUIRES_VALIDATION";
  reason: string;
  severity: "AMBER" | "RED";
  supporting_evidence_ids: string[];
  claim_evidence_ids: string[];
}
export interface LeadershipAction {
  action_id: string;
  description: string;
  supporting_evidence_ids: string[];
}
export interface KeyEvidence {
  evidence_id: string;
  description: string;
  dimensions: Dimension[];
  evidence_kind: string;
  source_type: string;
  source_name: string;
  source_reference: string;
  source_section: string | null;
  source_snippet: string | null;
}
export interface DashboardAssessment {
  project: string;
  assessment_date: string;
  assessment_version: string;
  reported_health: HealthStatus;
  programpulse_health: HealthStatus;
  status_conflict: boolean;
  confidence: Confidence;
  leadership_attention_required: boolean;
  dimension_summary: DimensionSummary[];
  top_governance_challenges: GovernanceChallenge[];
  top_recommended_actions: LeadershipAction[];
  executive_summary: string;
  key_evidence: KeyEvidence[];
}
export type AssessmentMode = "sample" | "live";
