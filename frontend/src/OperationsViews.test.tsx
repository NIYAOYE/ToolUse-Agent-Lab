import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "./test/setup";
import { App } from "./App";
import { renderApp } from "./test/renderApp";

function json(data: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(data), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("Phase 7 operations views", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("imports a CSV or JSON file through the multipart boundary", async () => {
    vi.mocked(fetch).mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (String(input) === "/v1/tickets/import" && init?.method === "POST") {
          return json({ imported_count: 2, tickets: [] }, 201);
        }
        throw new Error(`Unexpected request: ${String(input)}`);
      },
    );
    renderApp(<App />, "/tickets/import");

    const file = new File(
      ["id,title,description,environment,service,priority\nINC-1,A,B,prod,api,P1"],
      "tickets.csv",
      { type: "text/csv" },
    );
    fireEvent.change(screen.getByLabelText("CSV or JSON file"), {
      target: { files: [file] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Import tickets" }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/v1/tickets/import",
        expect.objectContaining({
          method: "POST",
          body: expect.any(FormData),
        }),
      );
    });
    expect(await screen.findByText("2 tickets imported")).toBeInTheDocument();
  });

  it("renders diagnosis-time count, median, and P75 from the API", async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      if (String(input) === "/v1/metrics/diagnosis-time") {
        return json({ count: 8, median_seconds: 42, p75_seconds: 61.5 });
      }
      throw new Error(`Unexpected request: ${String(input)}`);
    });
    renderApp(<App />, "/metrics");

    expect(await screen.findByText("8 diagnosed tickets")).toBeInTheDocument();
    expect(screen.getByText("42.0s")).toBeInTheDocument();
    expect(screen.getByText("61.5s")).toBeInTheDocument();
  });

  it("shows complete tool arguments and results in the audit view", async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/v1/investigations/7") {
        return json({
          investigation: {
            id: 7,
            ticket_id: "INC-42",
            session_id: "session-7",
            status: "AWAITING_REVIEW",
            started_at: "2026-06-15T12:00:00Z",
            diagnosed_at: "2026-06-15T12:04:00Z",
            completed_at: null,
            stop_reason: null,
            supplemental_instructions: null,
          },
          evidence: [
            {
              id: 11,
              investigation_id: 7,
              kind: "web_source",
              title: "Provider status evidence",
              summary: "The provider reported elevated response times.",
              source_ref: "https://status.example.test",
              tool_audit_id: 3,
              attachment_id: null,
              created_at: "2026-06-15T12:03:00Z",
            },
          ],
          report: null,
          approvals: [
            {
              id: 4,
              investigation_id: 7,
              decision: "approved_with_edits",
              original_draft: "Original response.",
              final_draft: "Reviewed response.",
              review_notes: "Clarified customer impact.",
              created_at: "2026-06-15T12:05:00Z",
            },
          ],
          events: [
            {
              id: 8,
              investigation_id: 7,
              event: "diagnosis_ready",
              payload: { confidence: 0.9 },
              created_at: "2026-06-15T12:04:00Z",
            },
          ],
        });
      }
      if (path === "/v1/investigations/7/audits") {
        return json([
          {
            id: 3,
            session_id: "session-7",
            call_id: "call-1",
            tool_name: "web_search",
            arguments: { query: "checkout latency" },
            result: { success: true, data: [{ title: "Provider status" }] },
            created_at: "2026-06-15T12:03:00Z",
          },
        ]);
      }
      throw new Error(`Unexpected request: ${path}`);
    });
    renderApp(<App />, "/audits/7");

    expect(await screen.findByText("web_search")).toBeInTheDocument();
    expect(screen.getByText(/"query": "checkout latency"/)).toBeInTheDocument();
    expect(screen.getByText(/"success": true/)).toBeInTheDocument();
    expect(screen.getByText("Diagnosis Ready")).toBeInTheDocument();
    expect(screen.getByText("Provider status evidence")).toBeInTheDocument();
    expect(screen.getByText("approved_with_edits")).toBeInTheDocument();
  });
});
