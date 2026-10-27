import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Dashboard from "../components/dashboard";
import { FILE_FIELDS } from "../lib/uploads";
import { sampleAssessment } from "../lib/sample-assessment";

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => { fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock); });
function open() { render(<Dashboard />); fireEvent.click(screen.getByRole("button", { name: "Analyze Project Evidence" })); }
function selectAll() {
  for (const field of FILE_FIELDS) fireEvent.change(screen.getByLabelText(field.label), {
    target: { files: [new File(["example"], field.key + (field.key === "status_report" ? ".md" : ".json"))] },
  });
}
const result = { ...sampleAssessment, project: "Uploaded Project" };
const response = (body: unknown, status = 200) => ({ ok: status === 200, status, json: vi.fn().mockResolvedValue(body) });

describe("evidence upload workflow", () => {
  it("shows all four required inputs, blocks incomplete selection and makes no request", () => {
    open();
    expect(screen.getByRole("heading", { name: "Analyze Project Evidence" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Assessment" })).toBeDisabled();
    for (const field of FILE_FIELDS) expect(screen.getByLabelText(field.label)).toBeInTheDocument();
    selectAll();
    expect(screen.getByRole("button", { name: "Run Assessment" })).toBeEnabled();
    expect(screen.getByText(/status_report.md — ready/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("rejects an unsupported extension and empty input", () => {
    open(); selectAll();
    fireEvent.change(screen.getByLabelText("RAID Log"), { target: { files: [new File(["x"], "raid.xlsm")] } });
    expect(screen.getByText("RAID Log has an unsupported file extension.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Assessment" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("RAID Log"), { target: { files: [new File([], "raid.json")] } });
    expect(screen.getByText("RAID Log is empty.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("sends four files once, shows progress and populates the existing live dashboard", async () => {
    let complete!: (response: unknown) => void;
    fetchMock.mockImplementation(() => new Promise(resolve => { complete = resolve; }));
    open(); selectAll();
    fireEvent.click(screen.getByRole("button", { name: "Run Assessment" }));
    expect(screen.getByRole("status")).toHaveTextContent("Examining project evidence...");
    const button = screen.getByRole("button", { name: "Examining project evidence..." });
    expect(button).toBeDisabled(); fireEvent.click(button);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/api\/v1\/ai\/assess-files$/);
    expect(init.method).toBe("POST");
    expect(init.headers).toBeUndefined(); // Browser supplies the multipart boundary.
    expect([...init.body.keys()]).toEqual(FILE_FIELDS.map(item => item.key));
    for (const field of FILE_FIELDS) expect(init.body.get(field.key)).toBeInstanceOf(File);
    await act(async () => complete(response(result)));
    expect(screen.getByRole("heading", { name: "Uploaded Project" })).toBeInTheDocument();
    expect(screen.getByText("LIVE ASSESSMENT", { selector: ".mode-badge" })).toBeInTheDocument();
    expect(within(screen.getByRole("article", { name: "Dependencies health" })).getByText("RED")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Governance challenges/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Start New Assessment" }));
    expect(screen.queryByRole("heading", { name: "Uploaded Project" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Assessment" })).toBeDisabled();
    for (const field of FILE_FIELDS) expect((screen.getByLabelText(field.label) as HTMLInputElement).files).toHaveLength(0);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it("maps validation errors to files and preserves selections for correction", async () => {
    fetchMock.mockResolvedValue(response({detail: {code: "invalid_file", field: "raid_log", reason: "json", message: "secret"}}, 422));
    open(); selectAll(); fireEvent.click(screen.getByRole("button", { name: "Run Assessment" }));
    await screen.findByRole("alert");
    expect(screen.getByText("RAID Log is not valid JSON.")).toBeInTheDocument();
    expect((screen.getByLabelText("RAID Log") as HTMLInputElement).files![0].name).toBe("raid_log.json");
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it.each([502,503,504,413])("retains files and safe errors on HTTP %s", async status => {
    fetchMock.mockResolvedValue(response({detail: "sk-private"}, status));
    open(); selectAll(); fireEvent.click(screen.getByRole("button", { name: "Run Assessment" }));
    await screen.findByRole("alert");
    expect(screen.getByText(/status_report.md — ready/)).toBeInTheDocument();
    expect(screen.queryByText(/sk-private/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Assessment" })).toBeEnabled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it("returns to sample without a request", () => {
    open(); selectAll(); fireEvent.click(screen.getByRole("button", { name: "View Sample Assessment" }));
    expect(screen.getByText("SAMPLE ASSESSMENT", {selector: ".mode-badge"})).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("enterprise file acceptance", () => {
  it.each([['Weekly Status Report','report.docx'], ['Weekly Status Report','report.pdf'], ['RAID Log','raid.xlsx'], ['Milestone Plan','plan.csv'], ['Quality / Defect Summary','quality.xlsx']])("accepts %s as %s without submitting", (label, name) => {
    open(); selectAll();
    fireEvent.change(screen.getByLabelText(label), {target: {files: [new File(['sample'],name)]}});
    expect(screen.getByRole('button',{name:'Run Assessment'})).toBeEnabled();
    expect(screen.getByText(new RegExp(name + ' — ready for server validation'))).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("shows friendly accepted-format guidance", () => {
    open();
    expect(screen.getByText(/Word, PDF or text document/)).toBeInTheDocument();
    expect(screen.getAllByText(/Excel, CSV or JSON file/)).toHaveLength(3);
  });
  it("shows safe PDF parsing feedback and preserves the selection", async () => {
    fetchMock.mockResolvedValue(response({detail:{field:'status_report',reason:'pdf_text',message:'provider private'}},422));
    open(); selectAll();
    fireEvent.change(screen.getByLabelText('Weekly Status Report'),{target:{files:[new File(['pdf'],'report.pdf')]}});
    fireEvent.click(screen.getByRole('button',{name:'Run Assessment'}));
    await screen.findByRole('alert');
    expect(screen.getByText(/contains insufficient machine-readable text/)).toBeInTheDocument();
    expect((screen.getByLabelText('Weekly Status Report') as HTMLInputElement).files![0].name).toBe('report.pdf');
    expect(screen.queryByText('provider private')).not.toBeInTheDocument();
  });
});
