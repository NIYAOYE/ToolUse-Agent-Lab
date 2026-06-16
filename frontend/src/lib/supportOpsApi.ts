import { apiRequest } from "./api";
import type { DiagnosisTimeMetrics, TicketPage } from "./contracts";

export const supportOpsApi = {
  listTickets(search = "") {
    return apiRequest<TicketPage>(`/v1/tickets${search}`);
  },
  diagnosisTimeMetrics() {
    return apiRequest<DiagnosisTimeMetrics>("/v1/metrics/diagnosis-time");
  },
};
