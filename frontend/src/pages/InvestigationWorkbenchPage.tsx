import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  ExternalLink,
  Play,
  RotateCcw,
  ShieldAlert,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../components/StatusBadge";
import type {
  ApprovalDecision,
  InvestigationDetail,
} from "../lib/contracts";
import { supportOpsApi } from "../lib/supportOpsApi";
import styles from "./InvestigationWorkbenchPage.module.css";

const terminalStatuses = new Set(["AWAITING_REVIEW", "FAILED", "APPROVED"]);

export function InvestigationWorkbenchPage() {
  const { ticketId = "" } = useParams();
  const queryClient = useQueryClient();
  const [startedInvestigationId, setStartedInvestigationId] = useState<
    number | null
  >(null);
  const [instructions, setInstructions] = useState("");
  const [finalDraft, setFinalDraft] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");

  const ticketQueue = useQuery({
    queryKey: ["tickets"],
    queryFn: () => supportOpsApi.listTickets(),
  });
  const ticketDetail = useQuery({
    queryKey: ["ticket", ticketId],
    queryFn: () => supportOpsApi.getTicket(ticketId),
    enabled: Boolean(ticketId),
  });
  const investigationId =
    startedInvestigationId ?? ticketDetail.data?.current_investigation?.id;
  const investigationDetail = useQuery({
    queryKey: ["investigation", investigationId],
    queryFn: () => supportOpsApi.getInvestigation(investigationId as number),
    enabled: investigationId !== undefined && investigationId !== null,
    refetchInterval: (query) => {
      const detail = query.state.data as InvestigationDetail | undefined;
      return detail && terminalStatuses.has(detail.investigation.status)
        ? false
        : 1500;
    },
  });

  const report =
    investigationDetail.data?.report ?? ticketDetail.data?.diagnosis_report;
  useEffect(() => {
    setStartedInvestigationId(null);
    setInstructions("");
    setFinalDraft("");
    setReviewNotes("");
  }, [ticketId]);

  useEffect(() => {
    if (report?.reply_draft) {
      setFinalDraft(report.reply_draft);
    }
  }, [report?.id, report?.reply_draft]);

  const start = useMutation({
    mutationFn: () => supportOpsApi.startInvestigation(ticketId, instructions),
    onSuccess: (investigation) => {
      setStartedInvestigationId(investigation.id);
      setInstructions("");
      void queryClient.invalidateQueries({ queryKey: ["ticket", ticketId] });
      void queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
  });

  const decide = useMutation({
    mutationFn: (decision: ApprovalDecision) =>
      supportOpsApi.decideInvestigation(
        investigationId as number,
        decision,
        finalDraft,
        reviewNotes,
      ),
    onSuccess: (response) => {
      queryClient.setQueryData<InvestigationDetail>(
        ["investigation", investigationId],
        (current) =>
          current
            ? {
                ...current,
                investigation: response.investigation,
                approvals: response.approvals,
              }
            : current,
      );
      void queryClient.invalidateQueries({ queryKey: ["ticket", ticketId] });
      void queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
  });

  const currentInvestigation = investigationDetail.data?.investigation;
  const canReview = currentInvestigation?.status === "AWAITING_REVIEW" && report;
  const approveDecision = useMemo<ApprovalDecision>(
    () =>
      finalDraft.trim() === report?.reply_draft.trim()
        ? "approved"
        : "approved_with_edits",
    [finalDraft, report?.reply_draft],
  );

  if (ticketDetail.isPending) {
    return <WorkbenchMessage title="Loading workbench" />;
  }
  if (ticketDetail.isError || !ticketDetail.data) {
    return <WorkbenchMessage title="Ticket unavailable" />;
  }

  const { ticket } = ticketDetail.data;

  return (
    <section aria-labelledby="workbench-title" className={styles.page}>
      <header className={styles.header}>
        <div>
          <Link className={styles.backLink} to="/tickets">
            <ArrowLeft aria-hidden="true" size={15} /> Ticket queue
          </Link>
          <span className={styles.coordinate}>WORKBENCH / {ticket.id}</span>
          <h1 id="workbench-title">{ticket.title}</h1>
        </div>
        <div className={styles.headerStatus}>
          <span>{ticket.priority}</span>
          <StatusBadge status={currentInvestigation?.status ?? ticket.status} />
        </div>
      </header>

      <div className={styles.workbench}>
        <aside aria-label="Ticket queue" className={styles.queuePanel}>
          <PanelHeader index="01" title="Ticket queue" />
          <div className={styles.ticketList}>
            {ticketQueue.data?.items.map((item) => (
              <Link
                aria-current={item.id === ticket.id ? "page" : undefined}
                className={styles.ticketItem}
                key={item.id}
                to={`/tickets/${encodeURIComponent(item.id)}`}
              >
                <span>{item.priority} / {item.id}</span>
                <strong>{item.title}</strong>
                <small>{item.service}</small>
              </Link>
            ))}
          </div>
          <dl className={styles.ticketFacts}>
            <div><dt>Service</dt><dd>{ticket.service}</dd></div>
            <div><dt>Environment</dt><dd>{ticket.environment}</dd></div>
            <div><dt>Category</dt><dd>{ticket.category ?? "Unclassified"}</dd></div>
            <div><dt>Source</dt><dd>{ticket.source}</dd></div>
          </dl>
          <div className={styles.ticketDescription}>
            <span>Incident statement</span>
            <p>{ticket.description}</p>
          </div>
        </aside>

        <section
          aria-label="Investigation details"
          className={styles.investigationPanel}
        >
          <PanelHeader index="02" title="Investigation" />
          {!investigationId && (
            <div className={styles.startBlock}>
              <ShieldAlert aria-hidden="true" size={26} />
              <h2>Human-directed investigation</h2>
              <p>Add optional boundaries, then start the controlled tool loop.</p>
              <label htmlFor="investigation-instructions">
                Supplemental instructions
              </label>
              <textarea
                id="investigation-instructions"
                onChange={(event) => setInstructions(event.target.value)}
                placeholder="Example: prioritize attached logs; do not infer customer impact."
                value={instructions}
              />
              <button
                disabled={start.isPending}
                onClick={() => start.mutate()}
                type="button"
              >
                <Play aria-hidden="true" size={15} />
                {start.isPending ? "Starting..." : "Start investigation"}
              </button>
              {start.isError && (
                <p className={styles.errorMessage} role="alert">
                  {errorMessage(start.error)}
                </p>
              )}
            </div>
          )}
          {investigationId && investigationDetail.isPending && (
            <WorkbenchMessage compact title="Loading investigation" />
          )}
          {investigationDetail.isError && (
            <p className={styles.errorMessage} role="alert">
              {errorMessage(investigationDetail.error)}
            </p>
          )}
          {investigationDetail.data && (
            <>
              <section className={styles.timeline}>
                <div className={styles.sectionTitle}>
                  <h2>Timeline</h2>
                  <StatusBadge
                    status={investigationDetail.data.investigation.status}
                  />
                </div>
                {investigationDetail.data.events.length === 0 ? (
                  <p className={styles.muted}>No events recorded yet.</p>
                ) : (
                  <ol>
                    {investigationDetail.data.events.map((event) => (
                      <li key={event.id}>
                        <span>{formatEvent(event.event)}</span>
                        <time>{formatTime(event.created_at)}</time>
                      </li>
                    ))}
                  </ol>
                )}
              </section>

              <section className={styles.evidenceSection}>
                <div className={styles.sectionTitle}>
                  <h2>Evidence</h2>
                  <span>
                    {investigationDetail.data.evidence.length} VERIFIED
                  </span>
                </div>
                <div className={styles.evidenceList}>
                  {investigationDetail.data.evidence.map((evidence) => (
                    <article key={evidence.id}>
                      <div>
                        <span>{evidence.kind.replaceAll("_", " ")}</span>
                        <strong>{evidence.title}</strong>
                      </div>
                      <p>{evidence.summary}</p>
                      {evidence.source_ref && (
                        <a
                          href={evidence.source_ref}
                          rel="noreferrer"
                          target="_blank"
                        >
                          Open source
                          <ExternalLink aria-hidden="true" size={12} />
                        </a>
                      )}
                    </article>
                  ))}
                </div>
              </section>
            </>
          )}
        </section>

        <aside aria-label="Diagnosis and review" className={styles.reviewPanel}>
          <PanelHeader index="03" title="Diagnosis review" />
          {!report && (
            <div className={styles.pendingReport}>
              <span>REPORT / PENDING</span>
              <p>
                The structured diagnosis will appear after the investigation
                completes.
              </p>
            </div>
          )}
          {report && (
            <>
              <div className={styles.reportSummary}>
                <div>
                  <span>Category</span>
                  <strong>{report.category}</strong>
                </div>
                <div>
                  <span>Confidence</span>
                  <strong>{Math.round(report.confidence * 100)}%</strong>
                </div>
                <div className={styles.rootCause}>
                  <span>Root cause</span>
                  <p>{report.root_cause}</p>
                </div>
                <div className={styles.rootCause}>
                  <span>Recommended actions</span>
                  <ol>
                    {report.recommended_actions.map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ol>
                </div>
              </div>

              <div className={styles.reviewForm}>
                <label htmlFor="final-reply">Final reply</label>
                <textarea
                  aria-label="Final reply"
                  disabled={!canReview}
                  id="final-reply"
                  onChange={(event) => setFinalDraft(event.target.value)}
                  value={finalDraft}
                />
                <label htmlFor="review-notes">Review notes</label>
                <textarea
                  disabled={!canReview}
                  id="review-notes"
                  onChange={(event) => setReviewNotes(event.target.value)}
                  placeholder="Required when returning the investigation."
                  value={reviewNotes}
                />
                {canReview && (
                  <div className={styles.reviewActions}>
                    <button
                      className={styles.approveButton}
                      disabled={!finalDraft.trim() || decide.isPending}
                      onClick={() => decide.mutate(approveDecision)}
                      type="button"
                    >
                      <Check aria-hidden="true" size={15} /> Approve diagnosis
                    </button>
                    <button
                      disabled={!reviewNotes.trim() || decide.isPending}
                      onClick={() => decide.mutate("returned")}
                      type="button"
                    >
                      <RotateCcw aria-hidden="true" size={15} /> Return
                    </button>
                  </div>
                )}
                {decide.isError && (
                  <p className={styles.errorMessage} role="alert">
                    {errorMessage(decide.error)}
                  </p>
                )}
              </div>
            </>
          )}
          {currentInvestigation?.status === "FAILED" && (
            <div className={styles.retryBlock}>
              <p>{currentInvestigation.stop_reason ?? "Investigation failed."}</p>
              <button
                disabled={start.isPending}
                onClick={() => start.mutate()}
                type="button"
              >
                <RotateCcw aria-hidden="true" size={15} /> Retry investigation
              </button>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}

function PanelHeader({ index, title }: { index: string; title: string }) {
  return (
    <header className={styles.panelHeader}>
      <span>{index}</span>
      <h2>{title}</h2>
    </header>
  );
}

function WorkbenchMessage({
  title,
  compact = false,
}: {
  title: string;
  compact?: boolean;
}) {
  return (
    <div className={compact ? styles.compactMessage : styles.message}>
      {title}
    </div>
  );
}

function formatEvent(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "The operation failed.";
}
