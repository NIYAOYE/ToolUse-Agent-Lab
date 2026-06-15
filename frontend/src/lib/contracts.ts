export type TicketStatus =
  | "NEW"
  | "QUEUED"
  | "INVESTIGATING"
  | "AWAITING_REVIEW"
  | "FAILED"
  | "APPROVED";

export type TicketPriority = "P1" | "P2" | "P3" | "P4";

export type Ticket = {
  id: string;
  title: string;
  description: string;
  environment: string;
  service: string;
  priority: TicketPriority;
  category: string | null;
  status: TicketStatus;
  source: "manual" | "csv_import" | "json_import";
  created_at: string;
  updated_at: string;
};

export type TicketPage = {
  items: Ticket[];
  total: number;
  page: number;
  page_size: number;
};

export type DiagnosisTimeMetrics = {
  count: number;
  median_seconds: number | null;
  p75_seconds: number | null;
};

export type InvestigationStatus =
  | "INVESTIGATING"
  | "AWAITING_REVIEW"
  | "FAILED"
  | "APPROVED";

export type EvidenceKind =
  | "attachment"
  | "tool_result"
  | "web_source"
  | "observation";

export type ApprovalDecision =
  | "approved"
  | "approved_with_edits"
  | "returned";

export type Investigation = {
  id: number;
  ticket_id: string;
  session_id: string;
  status: InvestigationStatus;
  started_at: string;
  diagnosed_at: string | null;
  completed_at: string | null;
  stop_reason: string | null;
  supplemental_instructions: string | null;
};

export type DiagnosisReport = {
  id: number;
  category: string;
  suggested_priority: TicketPriority;
  root_cause: string;
  confidence: number;
  evidence_ids: number[];
  recommended_actions: string[];
  reply_draft: string;
  created_at: string;
};

export type TicketDetail = {
  ticket: Ticket;
  current_investigation: Investigation | null;
  diagnosis_report: DiagnosisReport | null;
};

export type Evidence = {
  id: number;
  investigation_id: number;
  kind: EvidenceKind;
  title: string;
  summary: string;
  source_ref: string | null;
  tool_audit_id: number | null;
  attachment_id: number | null;
  created_at: string;
};

export type Approval = {
  id: number;
  investigation_id: number;
  decision: ApprovalDecision;
  original_draft: string;
  final_draft: string;
  review_notes: string;
  created_at: string;
};

export type InvestigationEvent = {
  id: number;
  investigation_id: number;
  event: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type InvestigationDetail = {
  investigation: Investigation;
  evidence: Evidence[];
  report: DiagnosisReport | null;
  approvals: Approval[];
  events: InvestigationEvent[];
};

export type InvestigationDecisionResponse = {
  investigation: Investigation;
  approvals: Approval[];
  should_run: boolean;
};
