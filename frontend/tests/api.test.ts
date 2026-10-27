import { describe, expect, it, vi } from "vitest";
import { isDashboardAssessment, runLiveAssessment } from "../lib/api";
import { sampleAssessment } from "../lib/sample-assessment";

describe("dashboard wire contract", () => {
  it("accepts the typed sample", () => { expect(isDashboardAssessment(sampleAssessment)).toBe(true); });
  it.each([
    { dimension_summary: sampleAssessment.dimension_summary.slice(1) },
    { dimension_summary: sampleAssessment.dimension_summary.map(() => sampleAssessment.dimension_summary[0]) },
    { programpulse_health: "BLUE" }, { confidence: null },
    { top_governance_challenges: [{ reason: "Incomplete" }] },
    { key_evidence: [{ source_name: "Incomplete" }] },
  ])("rejects incomplete or invalid data: %j", (change) => { expect(isDashboardAssessment({ ...sampleAssessment, ...change })).toBe(false); });
  it.each([503, 504, 502])("returns a safe error for HTTP %s without reading its body", async (status) => {
    const json = vi.fn();
    const fetch = vi.fn().mockResolvedValue({ ok: false, status, json });
    vi.stubGlobal("fetch", fetch);
    await expect(runLiveAssessment(new AbortController().signal)).rejects.toThrow();
    expect(json).not.toHaveBeenCalled();
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("honors the configured base URL and normalizes its trailing slash", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8900/");
    vi.resetModules();
    const configured = await import("../lib/api");
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => sampleAssessment });
    vi.stubGlobal("fetch", fetch);
    await configured.runLiveAssessment(new AbortController().signal);
    expect(fetch).toHaveBeenCalledWith("http://localhost:8900/api/v1/demo-ai-assessment/summary", expect.any(Object));
  });
});
