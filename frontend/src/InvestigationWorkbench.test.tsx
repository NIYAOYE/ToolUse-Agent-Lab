import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "./test/setup";
import { App } from "./App";
import { renderApp } from "./test/renderApp";

const ticket = {
  id: "INC-42",
  title: "Checkout latency spike",
  description: "Customers see elevated checkout latency.",
  environment: "production",
  service: "checkout-api",
  priority: "P1",
  category: "latency",
  status: "AWAITING_REVIEW",
  source: "manual",
  created_at: "2026-06-15T12:00:00Z",
  updated_at: "2026-06-15T12:05:00Z",
};

const investigation = {
  investigation: {
    id: 7,
    ticket_id: ticket.id,
    session_id: "session-7",
    status: "AWAITING_REVIEW",
    started_at: "2026-06-15T12:01:00Z",
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
      title: "Provider status",
      summary: "Payment provider reported elevated response times.",
      source_ref: "https://status.example.test/incidents/42",
      tool_audit_id: 3,
      attachment_id: null,
      created_at: "2026-06-15T12:03:00Z",
    },
  ],
  report: {
    id: 9,
    category: "dependency_latency",
    suggested_priority: "P1",
    root_cause: "Upstream payment provider latency increased checkout time.",
    confidence: 0.91,
    evidence_ids: [11],
    recommended_actions: ["Enable the provider fallback route."],
    reply_draft: "We identified elevated latency at the payment provider.",
    created_at: "2026-06-15T12:04:00Z",
  },
  approvals: [],
  events: [
    {
      id: 21,
      investigation_id: 7,
      event: "diagnosis_ready",
      payload: { evidence_count: 1 },
      created_at: "2026-06-15T12:04:00Z",
    },
  ],
};

function json(data: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(data), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("investigation workbench", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path === "/v1/tickets") {
          return json({ items: [ticket], total: 1, page: 1, page_size: 25 });
        }
        if (path === `/v1/tickets/${ticket.id}`) {
          return json({
            ticket,
            current_investigation: investigation.investigation,
            diagnosis_report: investigation.report,
          });
        }
        if (path === "/v1/investigations/7" && !init?.method) {
          return json(investigation);
        }
        if (path === "/v1/investigations/7/decision") {
          return json({
            investigation: {
              ...investigation.investigation,
              status: "APPROVED",
              completed_at: "2026-06-15T12:06:00Z",
            },
            approvals: [],
            should_run: false,
          });
        }
        throw new Error(`Unexpected request: ${path}`);
      }),
    );
  });

  it("selects a ticket, presents evidence, and approves the diagnosis", async () => {
    renderApp(<App />);

    fireEvent.click(
      await screen.findByRole("link", { name: "Open INC-42" }),
    );

    expect(
      await screen.findByRole("heading", { name: "Checkout latency spike" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Provider status")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Upstream payment provider latency increased checkout time.",
      ),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox", { name: "Final reply" }), {
      target: { value: "Provider fallback is active and latency is recovering." },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Approve diagnosis" }),
    );

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/v1/investigations/7/decision",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            decision: "approved_with_edits",
            final_draft:
              "Provider fallback is active and latency is recovering.",
            review_notes: "",
          }),
        }),
      );
    });
    expect(await screen.findAllByText("APPROVED")).not.toHaveLength(0);
  });

  it("starts a controlled investigation with supplemental instructions", async () => {
    const newTicket = { ...ticket, status: "NEW" };
    const activeInvestigation = {
      ...investigation.investigation,
      status: "INVESTIGATING",
      diagnosed_at: null,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path === "/v1/tickets") {
          return json({
            items: [newTicket],
            total: 1,
            page: 1,
            page_size: 25,
          });
        }
        if (path === `/v1/tickets/${ticket.id}` && !init?.method) {
          return json({
            ticket: newTicket,
            current_investigation: null,
            diagnosis_report: null,
          });
        }
        if (path === `/v1/tickets/${ticket.id}/investigations`) {
          return json(activeInvestigation, 202);
        }
        if (path === "/v1/investigations/7") {
          return json({
            investigation: activeInvestigation,
            evidence: [],
            report: null,
            approvals: [],
            events: [],
          });
        }
        throw new Error(`Unexpected request: ${path}`);
      }),
    );

    renderApp(<App />, `/tickets/${ticket.id}`);

    fireEvent.change(
      await screen.findByLabelText("Supplemental instructions"),
      { target: { value: "Prioritize attached gateway logs." } },
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Start investigation" }),
    );

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        `/v1/tickets/${ticket.id}/investigations`,
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            supplemental_instructions: "Prioritize attached gateway logs.",
          }),
        }),
      );
    });
    expect(await screen.findAllByText("INVESTIGATING")).not.toHaveLength(0);
  });
});
