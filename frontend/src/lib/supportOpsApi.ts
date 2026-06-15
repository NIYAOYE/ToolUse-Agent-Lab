import { apiRequest } from "./api";
import type {
  ApprovalDecision,
  DiagnosisTimeMetrics,
  Investigation,
  InvestigationDecisionResponse,
  InvestigationDetail,
  TicketDetail,
  TicketPage,
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
