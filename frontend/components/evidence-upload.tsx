"use client";
import { useEffect, useRef, useState } from "react";
import { assessFiles, FILE_FIELDS, UploadRequestError, validateFile, type EvidenceFiles, type FileErrors } from "../lib/uploads";
import type { DashboardAssessment } from "../lib/types";

export function EvidenceUpload({ onComplete, onSample }: { onComplete: (assessment: DashboardAssessment) => void; onSample: () => void }) {
  const [files, setFiles] = useState<EvidenceFiles>({});
  const [errors, setErrors] = useState<FileErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const pending = useRef(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const ready = FILE_FIELDS.every(({key}) => files[key] && !validateFile(key, files[key]!));
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!ready || pending.current) return;
    pending.current = true;
    setLoading(true); setError(null); setErrors({});
    const current = new AbortController(); controller.current = current;
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; current.abort(); }, 90_000);
    try {
      const assessment = await assessFiles(files, current.signal);
      if (!current.signal.aborted) onComplete(assessment);
    } catch (cause: unknown) {
      if (current.signal.aborted && !timedOut) return;
      if (cause instanceof UploadRequestError) { setError(cause.message); setErrors(cause.fields); }
      else setError(timedOut ? "The request took too long. The server may still be processing it. Your files are retained; no retry was made." : "Unable to reach or read the assessment service. Your files are retained; no retry was made.");
    } finally {
      clearTimeout(timer); pending.current = false;
      if (!current.signal.aborted || timedOut) setLoading(false);
    }
  }
  return <section className="upload-panel" aria-labelledby="upload-title">
    <div className="section-heading"><div><p className="eyebrow">PROJECT EVIDENCE INTAKE</p><h2 id="upload-title">Analyze Project Evidence</h2></div><button className="text-button" disabled={loading} onClick={onSample}>View Sample Assessment</button></div>
    <p className="upload-intro">Bring together the delivery narrative and operational records for one independent assessment.</p>
    <form onSubmit={submit} onReset={() => { setFiles({}); setErrors({}); setError(null); }}>
      <h3>1. Add project evidence</h3>
      <p className="upload-help">Use the supplied Excel templates or compatible CSV/JSON files. PDFs must contain selectable text. All sources must share a project name and reporting date. The report must include Project, Reporting date, Reported overall health and Target production release headers.</p>
      <div className="upload-grid">{FILE_FIELDS.map(spec => {
        const file = files[spec.key];
        const localError = file ? validateFile(spec.key, file) : undefined;
        const fieldError = errors[spec.key] || localError;
        return <div className="upload-field" key={spec.key}>
          <label htmlFor={spec.key}>{spec.label}</label>
          <p id={`${spec.key}-help`}>{spec.help} · up to 1 MB{spec.key === "status_report" ? " (TXT/MD: 100 KB)" : ""}</p>
          <input id={spec.key} type="file" accept={spec.accept} disabled={loading} aria-invalid={!!fieldError} aria-describedby={`${spec.key}-help ${spec.key}-state`} onChange={event => {
            const chosen = event.target.files?.[0];
            setFiles(previous => ({ ...previous, [spec.key]: chosen }));
            setErrors(previous => ({ ...previous, [spec.key]: undefined })); setError(null);
          }} />
          <p id={`${spec.key}-state`} className={fieldError ? "file-error" : "file-state"}>{fieldError || (file ? `${file.name} — ready for server validation (${file.name.split(".").pop()?.toUpperCase()})` : "Required · no file selected")}</p>
        </div>;
      })}</div>
      <h3>2. Review selected files</h3>
      <p className="upload-help">{FILE_FIELDS.filter(({key}) => files[key] && !validateFile(key, files[key]!)).length} of 4 files ready. Document readability, column mapping and evidence structure are checked before AI extraction.</p>
      <h3>3. Run ProgramPulse Assessment</h3>
      <p className="upload-help">Running an assessment performs one AI evidence-extraction request.</p>
      {error && <div role="alert" className="request-error">{error}</div>}
      {loading && <p role="status" className="request-status">Examining project evidence...</p>}
      <button className="live-button" disabled={!ready || loading} type="submit">{loading ? "Examining project evidence..." : "Run Assessment"}</button>
      <button className="text-button upload-reset" type="reset" disabled={loading}>Start New Assessment</button>
    </form>
  </section>;
}
