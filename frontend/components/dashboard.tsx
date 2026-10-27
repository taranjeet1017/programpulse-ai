"use client";

import { EvidenceUpload } from "./evidence-upload";
import { useEffect, useRef, useState } from "react";
import { runLiveAssessment, AssessmentRequestError } from "../lib/api";
import { sampleAssessment } from "../lib/sample-assessment";
import { DIMENSIONS, type AssessmentMode, type DashboardAssessment } from "../lib/types";
import { AssessmentModeBadge, DimensionCard, EvidenceCard, ExecutiveSummary, GovernanceChallengeCard, HealthComparison, LiveAssessmentButton, RecommendedAction } from "./assessment-parts";

export default function Dashboard() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadKey, setUploadKey] = useState(0);
  const [assessment, setAssessment] = useState<DashboardAssessment>(sampleAssessment);
  const [mode, setMode] = useState<AssessmentMode>("sample");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);
  const mounted = useRef(true);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; controller.current?.abort(); };
  }, []);

  async function runLive() {
    if (inFlight.current) return;
    inFlight.current = true;
    setLoading(true);
    setError(null);
    const current = new AbortController();
    controller.current = current;
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; current.abort(); }, 90_000);
    try {
      const result = await runLiveAssessment(current.signal);
      if (!mounted.current || current.signal.aborted) return;
      setAssessment(result);
      setMode("live");
    } catch (cause: unknown) {
      if (!mounted.current) return;
      setError(timedOut
        ? "The request took too long. The server may still be completing it. Your assessment is unchanged; no retry was made."
        : cause instanceof AssessmentRequestError ? cause.message
        : "Unable to reach or read the assessment service. Check your connection and backend. Your current assessment has been retained.");
    } finally {
      clearTimeout(timer);
      inFlight.current = false;
      if (mounted.current) setLoading(false);
    }
  }
  const orderedDimensions = DIMENSIONS.map((dimension) => assessment.dimension_summary.find((item) => item.dimension === dimension)!);
  const materialReasons = [...orderedDimensions].filter((item) => item.status !== "GREEN")
    .sort((a, b) => {
      const rank = { RED: 0, AMBER: 1, GREEN: 2 };
      const priority = ["DEPENDENCIES", "SCHEDULE", "QUALITY", "SCOPE", "ACTIONS", "GOVERNANCE"];
      return rank[a.status] - rank[b.status] || priority.indexOf(a.dimension) - priority.indexOf(b.dimension);
    }).slice(0, 3);
  const reportingDate = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(assessment.assessment_date + "T00:00:00Z"));

  return <>
    <a href="#main-content" className="skip-link">Skip to assessment</a>
    <header className="app-header"><div className="header-inner">
      <a href="#main-content" className="brand" aria-label="ProgramPulse AI dashboard"><span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 28 28" fill="none"><path d="M4 15h5l3-8 5 15 3-7h4" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" /></svg></span><span><strong>ProgramPulse <span className="brand-ai">AI</span></strong><small>Agentic Delivery &amp; Governance Platform</small></span></a>
      {!uploadOpen && <nav aria-label="Dashboard sections"><a href="#overview">Overview</a><a href="#challenges">Challenges</a><a href="#evidence">Evidence</a></nav>}
      <span className="header-context">DELIVERY ASSURANCE</span>
    </div></header>
    <main id="main-content" className="dashboard-shell">
      {!uploadOpen && <div className="workflow-toolbar"><button className="workflow-button" disabled={loading} onClick={() => setUploadOpen(true)}>Analyze Project Evidence</button><button className="text-button" disabled={loading} onClick={() => { controller.current?.abort(); setAssessment(sampleAssessment); setMode("sample"); setError(null); setUploadKey(key => key + 1); setUploadOpen(true); }}>Start New Assessment</button></div>}
      {uploadOpen ? <EvidenceUpload key={uploadKey} onSample={() => { setAssessment(sampleAssessment); setMode("sample"); setError(null); setUploadOpen(false); }} onComplete={result => { setAssessment(result); setMode("live"); setError(null); setUploadOpen(false); }} /> : <>
      <section className="project-header" id="overview" aria-labelledby="project-title"><div>
        <div className="breadcrumb">PROJECT INTELLIGENCE <span aria-hidden="true">/</span> EXECUTIVE OVERVIEW</div>
        <h1 id="project-title">{assessment.project}</h1>
        <div className="project-meta"><AssessmentModeBadge mode={mode} /><span>As of <time dateTime={assessment.assessment_date}>{reportingDate}</time></span><span><strong>{assessment.confidence}</strong> confidence</span><span>Assessment v{assessment.assessment_version}</span></div>
      </div><LiveAssessmentButton loading={loading} onClick={runLive} /></section>
      <div className="mode-context"><span>{mode === "sample" ? "Illustrative evidence snapshot. Explore the dashboard without using API credits." : "Live extraction completed. Health decisions remain deterministic and evidence-led."}</span>{mode === "live" && <button disabled={loading} onClick={() => { setAssessment(sampleAssessment); setMode("sample"); setError(null); }}>Return to sample</button>}</div>
      {loading && <div role="status" className="request-status"><span className="spinner" aria-hidden="true" /><div><strong>Examining project evidence...</strong><p>Your current assessment stays visible while the evidence is reviewed.</p></div></div>}
      {error && <div role="alert" className="request-error"><strong>Live assessment not completed</strong><p>{error}</p><small>No automatic retry was made.</small></div>}
      <HealthComparison assessment={assessment} />
      <ExecutiveSummary assessment={assessment} />
      <section className="dashboard-section" aria-labelledby="dimensions-title"><div className="section-heading"><div><p className="eyebrow">THE DELIVERY PICTURE</p><h2 id="dimensions-title">Independent Delivery Assessment</h2></div><p>Six lenses. One independent assessment.</p></div><div className="dimension-grid">{orderedDimensions.map((item) => <DimensionCard key={item.dimension} data={item} />)}</div></section>
      <section className="dashboard-section disagreement-section" aria-labelledby="disagreement-title"><div className="section-heading"><div><p className="eyebrow">BEHIND THE ASSESSMENT</p><h2 id="disagreement-title">{assessment.status_conflict ? "Why ProgramPulse disagrees" : "What the evidence shows"}</h2></div><p>Material signals requiring attention</p></div>
        {materialReasons.length ? <ol className="material-reasons">{materialReasons.map((item, index) => <li key={item.dimension}><span className="reason-number">0{index + 1}</span><div><h3>{item.dimension[0] + item.dimension.slice(1).toLowerCase()}</h3><p>{item.headline_reason}</p></div></li>)}</ol> : <p className="empty-state">No adverse delivery signals were identified by the current governance rules.</p>}
      </section>
      <section id="challenges" className="dashboard-section" aria-labelledby="challenges-title"><div className="section-heading"><div><p className="eyebrow">CLAIMS MEET EVIDENCE</p><h2 id="challenges-title">Governance challenges <span className="section-count">{assessment.top_governance_challenges.length}</span></h2></div><p>Expand a claim to examine the evidence</p></div>
        <div className="challenge-list">{assessment.top_governance_challenges.map((item, index) => <GovernanceChallengeCard key={item.challenge_id} data={item} index={index} evidence={assessment.key_evidence} />)}</div>
        {!assessment.top_governance_challenges.length && <p className="empty-state">No governance challenges in this assessment.</p>}
      </section>
      <section className="dashboard-section" aria-labelledby="actions-title"><div className="section-heading"><div><p className="eyebrow">FROM INSIGHT TO INTERVENTION</p><h2 id="actions-title">Recommended leadership actions</h2></div><p>Ordered for leadership review</p></div><ol className="action-list">{assessment.top_recommended_actions.map((item, index) => <RecommendedAction key={item.action_id} data={item} index={index} />)}</ol>{!assessment.top_recommended_actions.length && <p className="empty-state">No leadership actions are required by the current rules.</p>}</section>
      <section id="evidence" className="dashboard-section" aria-labelledby="evidence-title"><div className="section-heading"><div><p className="eyebrow">A TRACEABLE POINT OF VIEW</p><h2 id="evidence-title">Key evidence <span className="section-count">{assessment.key_evidence.length}</span></h2></div><p>Prioritized source records · not the full audit catalog</p></div><div className="evidence-grid">{assessment.key_evidence.map((item) => <EvidenceCard key={item.evidence_id} data={item} />)}</div>{!assessment.key_evidence.length && <p className="empty-state">No key evidence was prioritized in this assessment.</p>}</section>
      </>}
      <footer className="dashboard-footer"><strong>ProgramPulse AI</strong><span>AI interprets evidence. Governance rules determine health.</span><span>{mode === "sample" ? "SAMPLE ASSESSMENT · NO API USAGE" : "LIVE ASSESSMENT"}</span></footer>
    </main>
  </>;
}
