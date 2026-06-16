import { apiRequest } from "./api";
import type {
  ApprovalDecision,
  DiagnosisTimeMetrics,
  Investigation,
  InvestigationDecisionResponse,
  InvestigationDetail,
  TicketDetail,
  TicketImportResponse,
  TicketPage,
  ToolAudit,
} from "./contracts";

function jsonRequest(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const supportOpsApi = {
  listTickets(search = "") {
    return apiRequest<TicketPage>(`/v1/tickets${search}`);
  },
  getTicket(ticketId: string) {
    return apiRequest<TicketDetail>(
      `/v1/tickets/${encodeURIComponent(ticketId)}`,
    );
  },
  deleteTicket(ticketId: string) {
    return apiRequest<void>(`/v1/tickets/${encodeURIComponent(ticketId)}`, {
      method: "DELETE",
    });
  },
  importTickets(file: File) {
    const form = new FormData();
    form.append("file", file);
    return apiRequest<TicketImportResponse>("/v1/tickets/import", {
      method: "POST",
      body: form,
    });
  },
  startInvestigation(ticketId: string, supplementalInstructions: string) {
    return apiRequest<Investigation>(
      `/v1/tickets/${encodeURIComponent(ticketId)}/investigations`,
      jsonRequest(
        supplementalInstructions.trim()
          ? { supplemental_instructions: supplementalInstructions.trim() }
          : {},
      ),
    );
  },
  getInvestigation(investigationId: number) {
    return apiRequest<InvestigationDetail>(
      `/v1/investigations/${investigationId}`,
    );
  },
  listInvestigationAudits(investigationId: number) {
    return apiRequest<ToolAudit[]>(
      `/v1/investigations/${investigationId}/audits`,
    );
  },
  decideInvestigation(
    investigationId: number,
    decision: ApprovalDecision,
    finalDraft: string,
    reviewNotes: string,
  ) {
    return apiRequest<InvestigationDecisionResponse>(
      `/v1/investigations/${investigationId}/decision`,
      jsonRequest({
        decision,
        final_draft: finalDraft,
        review_notes: reviewNotes,
      }),
    );
  },
  diagnosisTimeMetrics() {
    return apiRequest<DiagnosisTimeMetrics>("/v1/metrics/diagnosis-time");
  },
};
