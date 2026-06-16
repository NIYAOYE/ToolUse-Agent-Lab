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
