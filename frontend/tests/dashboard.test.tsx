import { StrictMode } from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Dashboard from "../components/dashboard";
import { sampleAssessment } from "../lib/sample-assessment";
import { API_BASE_URL, SUMMARY_PATH } from "../lib/api";
import { DIMENSIONS, type DashboardAssessment } from "../lib/types";

const live: DashboardAssessment = { ...sampleAssessment, project: "AssessPro — updated evidence", programpulse_health: "RED", assessment_version: "1.1" };
const response = (body: unknown, status = 200) => ({ ok: status === 200, status, json: vi.fn().mockResolvedValue(body) }) as unknown as Response;
let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => { fetchMock = vi.fn().mockRejectedValue(new Error("Network is forbidden in tests")); vi.stubGlobal("fetch", fetchMock); });

function startLive() { fireEvent.click(screen.getByRole("button", { name: "Run Live Assessment" })); }

describe("default sample experience", () => {
  it("keeps shortened reasons traceable and derives the leadership headline from health", () => {
    render(<Dashboard />);
    expect(screen.getByRole("heading", { name: "Independent Delivery Assessment" })).toBeInTheDocument();
    expect(screen.getByText("Evidence supports AMBER, challenging the reported GREEN position.")).toBeInTheDocument();
    const card = screen.getByRole("article", { name: "Dependencies health" });
    const reason = sampleAssessment.dimension_summary.find(item => item.dimension === "DEPENDENCIES")!.headline_reason;
    expect(card.querySelector(":scope > p")!.textContent!.length).toBeLessThanOrEqual(100);
    fireEvent.click(within(card).getByText("Full reason"));
    expect(card.querySelector("details")).toHaveAttribute("open");
    expect(within(card).getByText(reason)).toBeVisible();
    for (const name of ["Overview", "Challenges", "Evidence"]) {
      const link = screen.getByRole("link", { name });
      expect(document.querySelector(link.getAttribute("href")!)).not.toBeNull();
    }
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("renders sample health comparison and conflict without a backend call, including Strict Mode", () => {
    render(<StrictMode><Dashboard /></StrictMode>);
    expect(screen.getByText("SAMPLE ASSESSMENT", { selector: ".mode-badge" })).toBeInTheDocument();
    expect(within(screen.getByRole("article", { name: "Reported Health" })).getByText("GREEN")).toBeInTheDocument();
    expect(within(screen.getByRole("article", { name: "ProgramPulse Assessment" })).getByText("AMBER")).toBeInTheDocument();
    expect(screen.getByText("STATUS CONFLICT")).toBeInTheDocument();
    expect(screen.getByText("Leadership Attention Required")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("renders all six dimensions and highlights Dependencies RED", () => {
    render(<Dashboard />);
    for (const dimension of DIMENSIONS) {
      const name = dimension[0] + dimension.slice(1).toLowerCase();
      expect(screen.getByRole("article", { name: `${name} health` })).toBeInTheDocument();
    }
    expect(within(screen.getByRole("article", { name: "Dependencies health" })).getByText("RED")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("exposes provenance on expansion without fetching full evidence", () => {
    render(<Dashboard />);
    const summary = document.querySelector(".challenge-card summary")!;
    fireEvent.click(summary);
    expect(document.querySelector(".challenge-card")).toHaveAttribute("open");
    expect(screen.getAllByText("Supporting delivery evidence").length).toBeGreaterThan(0);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("explicit live assessment", () => {
  it("makes one summary request, disables the button and preserves sample while pending", async () => {
    let complete!: (value: Response) => void;
    fetchMock.mockImplementation(() => new Promise<Response>((resolve) => { complete = resolve; }));
    render(<Dashboard />);
    startLive();
    const button = screen.getByRole("button", { name: "Examining project evidence..." });
    expect(button).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Examining project evidence...");
    expect(screen.getByText("SAMPLE ASSESSMENT", { selector: ".mode-badge" })).toBeInTheDocument();
    fireEvent.click(button);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}${SUMMARY_PATH}`, expect.objectContaining({ method: "GET", cache: "no-store", credentials: "omit", signal: expect.any(AbortSignal) }));
    await act(async () => complete(response(live)));
    expect(screen.getByText("LIVE ASSESSMENT", { selector: ".mode-badge" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: live.project })).toBeInTheDocument();
    expect(within(screen.getByRole("article", { name: "ProgramPulse Assessment" })).getByText("RED")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Live Assessment" })).toBeEnabled();
  });
  it("retains sample on failure, exposes a safe error and never retries", async () => {
    const failed = response({ detail: "sk-secret provider stack trace" }, 502);
    fetchMock.mockResolvedValue(failed);
    render(<Dashboard />);
    startLive();
    expect(await screen.findByRole("alert")).toHaveTextContent("Live assessment not completed");
    expect(screen.getByRole("heading", { name: sampleAssessment.project })).toBeInTheDocument();
    expect(screen.getByText("SAMPLE ASSESSMENT", { selector: ".mode-badge" })).toBeInTheDocument();
    expect(screen.queryByText(/sk-secret/)).not.toBeInTheDocument();
    expect(failed.json).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Run Live Assessment" })).toBeEnabled();
  });
  it("retains the last live result when a later run fails", async () => {
    fetchMock.mockResolvedValueOnce(response(live)).mockRejectedValueOnce(new Error("private transport detail"));
    render(<Dashboard />);
    startLive();
    await screen.findByRole("heading", { name: live.project });
    startLive();
    await screen.findByRole("alert");
    expect(screen.getByRole("heading", { name: live.project })).toBeInTheDocument();
    expect(screen.getByText("LIVE ASSESSMENT", { selector: ".mode-badge" })).toBeInTheDocument();
    expect(screen.queryByText(/private transport detail/)).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
  it("rejects malformed success data without replacing the assessment", async () => {
    fetchMock.mockResolvedValue(response({ project: "Invalid result" }));
    render(<Dashboard />);
    startLive();
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be validated");
    expect(screen.getByRole("heading", { name: sampleAssessment.project })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it("can return to sample mode without any additional call", async () => {
    fetchMock.mockResolvedValue(response(live));
    render(<Dashboard />);
    startLive();
    await screen.findByRole("heading", { name: live.project });
    fireEvent.click(screen.getByRole("button", { name: "Return to sample" }));
    expect(screen.getByText("SAMPLE ASSESSMENT", { selector: ".mode-badge" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it("aborts an in-flight request when the dashboard unmounts", () => {
    fetchMock.mockImplementation(() => new Promise(() => {}));
    const view = render(<Dashboard />);
    startLive();
    const signal = fetchMock.mock.calls[0][1].signal as AbortSignal;
    view.unmount();
    expect(signal.aborted).toBe(true);
  });
  it("shows agreement and no-intervention states from the live result", async () => {
    fetchMock.mockResolvedValue(response({ ...live, reported_health: "GREEN", programpulse_health: "GREEN", status_conflict: false, leadership_attention_required: false, dimension_summary: live.dimension_summary.map((item) => ({ ...item, status: "GREEN" })), top_governance_challenges: [], top_recommended_actions: [], key_evidence: [] }));
    render(<Dashboard />);
    startLive();
    await waitFor(() => expect(screen.getByText("STATUS ALIGNED")).toBeInTheDocument());
    expect(screen.queryByText("STATUS CONFLICT")).not.toBeInTheDocument();
    expect(screen.getByText("No Leadership Intervention Required")).toBeInTheDocument();
    expect(screen.getByText("No governance challenges in this assessment.")).toBeInTheDocument();
  });
});
