import type { AssessmentMode, DashboardAssessment, DimensionSummary, GovernanceChallenge, HealthStatus, KeyEvidence, LeadershipAction } from "../lib/types";

export function StatusBadge({ status }: { status: HealthStatus }) {
  return <span className={`status-badge status-${status.toLowerCase()}`}><span className="status-dot" aria-hidden="true" />{status}</span>;
}
export function AssessmentModeBadge({ mode }: { mode: AssessmentMode }) {
  return <span className={`mode-badge ${mode}`}><span aria-hidden="true">{mode === "sample" ? "◌" : "●"}</span>{mode.toUpperCase()} ASSESSMENT</span>;
}
export function LiveAssessmentButton({ loading, onClick }: { loading: boolean; onClick: () => void }) {
  return <div className="live-control"><button className="live-button" disabled={loading} onClick={onClick}>
    {loading ? <><span className="spinner" aria-hidden="true" />Examining project evidence...</> : <>Run Live Assessment <span aria-hidden="true">↗</span></>}
  </button><p>Runs one AI evidence-extraction request.</p></div>;
}
export function HealthComparison({ assessment }: { assessment: DashboardAssessment }) {
  return <section aria-label="Reported and independent health comparison" className="health-comparison">
    <div className="comparison-grid">
      <article className="health-card reported" aria-labelledby="reported-health-title">
        <div className="health-eyebrow"><span className="eyebrow">Management position</span><span className="card-number">01</span></div>
        <h2 id="reported-health-title">Reported Health</h2>
        <p className={`health-word text-${assessment.reported_health.toLowerCase()}`}>{assessment.reported_health}</p>
        <p className="health-caption">As stated in the weekly status report</p>
      </article>
      <span className="comparison-bridge" aria-hidden="true">⇄</span>
      <article className={`health-card independent assessment-${assessment.programpulse_health.toLowerCase()}`} aria-labelledby="independent-health-title">
        <div className="health-eyebrow"><span className="eyebrow">Independent delivery assurance</span><span className="card-number">02</span></div>
        <h2 id="independent-health-title">ProgramPulse Assessment</h2>
        <p className={`health-word text-${assessment.programpulse_health.toLowerCase()}`}>{assessment.programpulse_health}</p>
        <p className="health-caption">Determined by governance rules, grounded in evidence</p>
      </article>
    </div>
    <div className={`conflict-strip ${assessment.status_conflict ? "conflicted" : "aligned"}`}>
      <div><span className="conflict-icon" aria-hidden="true">{assessment.status_conflict ? "!" : "✓"}</span><strong>{assessment.status_conflict ? "STATUS CONFLICT" : "STATUS ALIGNED"}</strong><span className="conflict-description">{assessment.status_conflict ? "Reported and evidenced project health do not agree." : "Reported and independently assessed health agree."}</span></div>
      <span className={`attention-label ${assessment.leadership_attention_required ? "attention-required" : ""}`}>{assessment.leadership_attention_required ? "Leadership Attention Required" : "No Leadership Intervention Required"}</span>
    </div>
  </section>;
}
export function ExecutiveSummary({ assessment }: { assessment: DashboardAssessment }) {
  const headline = assessment.status_conflict
    ? `Evidence supports ${assessment.programpulse_health}, challenging the reported ${assessment.reported_health} position.`
    : `Reported and independent health align at ${assessment.programpulse_health}.`;
  return <section className="executive-summary" aria-labelledby="executive-title"><div className="section-caption"><h2 id="executive-title">ProgramPulse View</h2><span>LEADERSHIP BRIEF</span></div><h3 className="executive-headline">{headline}</h3><p>{assessment.executive_summary}</p></section>;
}
export function DimensionCard({ data }: { data: DimensionSummary }) {
  const name = data.dimension[0] + data.dimension.slice(1).toLowerCase();
  // Shorten presentation only; retain the exact source reason in accessible details.
  const reason = data.headline_reason;
  const shortened = reason.length > 100;
  const headline = shortened ? reason.slice(0, 97).replace(/\s+\S*$/, "") + "…" : reason;
  return <article className={`dimension-card ${data.status === "RED" ? "dimension-critical" : ""}`} aria-label={`${name} health`}>
    <h3>{name}</h3><StatusBadge status={data.status} /><p>{headline}</p>
    {shortened && <details className="dimension-details"><summary>Full reason<span className="sr-only"> for {name}</span></summary><p>{reason}</p></details>}
    <span className="evidence-count">{data.evidence_count} supporting {data.evidence_count === 1 ? "record" : "records"}</span>
  </article>;
}
function EvidenceReferences({ ids, evidence }: { ids: string[]; evidence: KeyEvidence[] }) {
  return <ul className="reference-list">{[...new Set(ids)].map((id) => {
    const source = evidence.find((item) => item.evidence_id === id);
    return <li key={id}><code>{id}</code>{source ? <span>{source.source_name} · {source.description}</span> : <span>Referenced in the detailed audit catalog; not included in this compact shortlist.</span>}</li>;
  })}</ul>;
}
export function GovernanceChallengeCard({ data, evidence, index }: { data: GovernanceChallenge; evidence: KeyEvidence[]; index: number }) {
  return <details className="challenge-card"><summary>
    <span className="row-index">{String(index + 1).padStart(2, "0")}</span>
    <div className="challenge-claim"><span className="eyebrow">Reported claim</span><h3>“{data.reported_claim}”</h3></div>
    <div className="challenge-meta"><StatusBadge status={data.severity} /><span>{new Set(data.supporting_evidence_ids).size} supporting records</span></div><span className="expand-indicator" aria-hidden="true">+</span>
  </summary><div className="challenge-body"><span className="eyebrow">ProgramPulse challenge</span><p>{data.reason}</p><span className="challenge-outcome">{data.assessment.replaceAll("_", " ")}</span>
    <h4>Supporting delivery evidence</h4><EvidenceReferences ids={data.supporting_evidence_ids} evidence={evidence} />
    <h4>Reported claim references</h4><EvidenceReferences ids={data.claim_evidence_ids} evidence={evidence} />
  </div></details>;
}
export function RecommendedAction({ data, index }: { data: LeadershipAction; index: number }) {
  return <li className="action-card"><span className="action-priority">{String(index + 1).padStart(2, "0")}</span><div><h3>{data.description}</h3><p>{new Set(data.supporting_evidence_ids).size} supporting evidence records</p></div><span className="action-arrow" aria-hidden="true">↗</span></li>;
}
const sourceLabels: Record<string, string> = { RAID_LOG: "RAID log", MILESTONE_PLAN: "Milestone plan", QUALITY_DATA: "Quality data", AI_STATUS_REPORT: "Status report" };
export function EvidenceCard({ data }: { data: KeyEvidence }) {
  return <article className="evidence-card"><div className="evidence-topline"><span className="source-label">{sourceLabels[data.source_type] || data.source_type.replaceAll("_", " ")}</span><span className="evidence-kind">{data.evidence_kind.replaceAll("_", " ")}</span></div>
    <h3>{data.description}</h3><p className="evidence-dimensions">{data.dimensions.join(" / ")}</p>
    {data.source_snippet && <blockquote>{data.source_snippet}</blockquote>}
    <div className="source-reference"><span>Source reference</span><code>{data.source_reference}</code></div><code className="evidence-id">{data.evidence_id}</code>
  </article>;
}
