import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  ClipboardList,
  ExternalLink,
  Play,
  RotateCcw,
  ShieldAlert,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";
import type {
  ApprovalDecision,
  InvestigationDetail,
} from "../lib/contracts";
import { supportOpsApi } from "../lib/supportOpsApi";
import styles from "./InvestigationWorkbenchPage.module.css";

const terminalStatuses = new Set(["AWAITING_REVIEW", "FAILED", "APPROVED"]);

export function InvestigationWorkbenchPage() {
  const { t } = useI18n();
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
    return <WorkbenchMessage title={t("workbench.loading")} />;
  }
  if (ticketDetail.isError || !ticketDetail.data) {
    return <WorkbenchMessage title={t("workbench.unavailable")} />;
  }

  const { ticket } = ticketDetail.data;

  return (
    <section aria-labelledby="workbench-title" className={styles.page}>
      <header className={styles.header}>
        <div>
          <Link className={styles.backLink} to="/tickets">
            <ArrowLeft aria-hidden="true" size={15} /> {t("workbench.back")}
          </Link>
          <span className={styles.coordinate}>WORKBENCH / {ticket.id}</span>
          <h1 id="workbench-title">{ticket.title}</h1>
        </div>
        <div className={styles.headerStatus}>
          <span>{ticket.priority}</span>
          <StatusBadge status={currentInvestigation?.status ?? ticket.status} />
          {investigationId && (
            <Link className={styles.auditLink} to={`/audits/${investigationId}`}>
              <ClipboardList aria-hidden="true" size={14} /> {t("workbench.audit")}
            </Link>
          )}
        </div>
      </header>

      <div className={styles.workbench}>
        <aside aria-label={t("workbench.queue")} className={styles.queuePanel}>
          <PanelHeader index="01" title={t("workbench.queue")} />
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
            <div><dt>{t("workbench.service")}</dt><dd>{ticket.service}</dd></div>
            <div><dt>{t("workbench.environment")}</dt><dd>{ticket.environment}</dd></div>
            <div><dt>{t("workbench.category")}</dt><dd>{ticket.category ?? t("workbench.unclassified")}</dd></div>
            <div><dt>{t("workbench.source")}</dt><dd>{ticket.source}</dd></div>
          </dl>
          <div className={styles.ticketDescription}>
            <span>{t("workbench.incident")}</span>
            <p>{ticket.description}</p>
          </div>
        </aside>

        <section
          aria-label={t("workbench.details")}
          className={styles.investigationPanel}
        >
          <PanelHeader index="02" title={t("workbench.investigation")} />
          {!investigationId && (
            <div className={styles.startBlock}>
              <ShieldAlert aria-hidden="true" size={26} />
              <h2>{t("workbench.directed")}</h2>
              <p>{t("workbench.startDescription")}</p>
              <label htmlFor="investigation-instructions">
                {t("workbench.instructions")}
              </label>
              <textarea
                id="investigation-instructions"
                onChange={(event) => setInstructions(event.target.value)}
                placeholder={t("workbench.instructionsPlaceholder")}
                value={instructions}
              />
              <button
                disabled={start.isPending}
                onClick={() => start.mutate()}
                type="button"
              >
                <Play aria-hidden="true" size={15} />
                {start.isPending ? t("workbench.starting") : t("workbench.start")}
              </button>
              {start.isError && (
                <p className={styles.errorMessage} role="alert">
                  {errorMessage(start.error, t("workbench.operationFailed"))}
                </p>
              )}
            </div>
          )}
          {investigationId && investigationDetail.isPending && (
            <WorkbenchMessage compact title={t("workbench.loadingInvestigation")} />
          )}
          {investigationDetail.isError && (
            <p className={styles.errorMessage} role="alert">
              {errorMessage(
                investigationDetail.error,
                t("workbench.operationFailed"),
              )}
            </p>
          )}
          {investigationDetail.data && (
            <>
              <section className={styles.timeline}>
                <div className={styles.sectionTitle}>
                  <h2>{t("workbench.timeline")}</h2>
                  <StatusBadge
                    status={investigationDetail.data.investigation.status}
                  />
                </div>
                {investigationDetail.data.events.length === 0 ? (
                  <p className={styles.muted}>{t("workbench.noEvents")}</p>
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
                  <h2>{t("workbench.evidence")}</h2>
                  <span>
                    {investigationDetail.data.evidence.length} {t("workbench.verified")}
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
                          {t("workbench.openSource")}
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

        <aside aria-label={t("workbench.review")} className={styles.reviewPanel}>
          <PanelHeader index="03" title={t("workbench.review")} />
          {!report && (
            <div className={styles.pendingReport}>
              <span>{t("workbench.reportPending")}</span>
              <p>{t("workbench.reportPendingDetail")}</p>
            </div>
          )}
          {report && (
            <>
              <div className={styles.reportSummary}>
                <div>
                  <span>{t("workbench.reportCategory")}</span>
                  <strong>{report.category}</strong>
                </div>
                <div>
                  <span>{t("workbench.confidence")}</span>
                  <strong>{Math.round(report.confidence * 100)}%</strong>
                </div>
                <div className={styles.rootCause}>
                  <span>{t("workbench.rootCause")}</span>
                  <p>{report.root_cause}</p>
                </div>
                <div className={styles.rootCause}>
                  <span>{t("workbench.recommendedActions")}</span>
                  <ol>
                    {report.recommended_actions.map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ol>
                </div>
              </div>

              <div className={styles.reviewForm}>
                <label htmlFor="final-reply">{t("workbench.finalReply")}</label>
                <textarea
                  aria-label={t("workbench.finalReply")}
                  disabled={!canReview}
                  id="final-reply"
                  onChange={(event) => setFinalDraft(event.target.value)}
                  value={finalDraft}
                />
                <label htmlFor="review-notes">{t("workbench.reviewNotes")}</label>
                <textarea
                  disabled={!canReview}
                  id="review-notes"
                  onChange={(event) => setReviewNotes(event.target.value)}
                  placeholder={t("workbench.reviewPlaceholder")}
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
                      <Check aria-hidden="true" size={15} /> {t("workbench.approve")}
                    </button>
                    <button
                      disabled={!reviewNotes.trim() || decide.isPending}
                      onClick={() => decide.mutate("returned")}
                      type="button"
                    >
                      <RotateCcw aria-hidden="true" size={15} /> {t("workbench.return")}
                    </button>
                  </div>
                )}
                {decide.isError && (
                  <p className={styles.errorMessage} role="alert">
                    {errorMessage(decide.error, t("workbench.operationFailed"))}
                  </p>
                )}
              </div>
            </>
          )}
          {currentInvestigation?.status === "FAILED" && (
            <div className={styles.retryBlock}>
              <p>{currentInvestigation.stop_reason ?? t("workbench.failed")}</p>
              <button
                disabled={start.isPending}
                onClick={() => start.mutate()}
                type="button"
              >
                <RotateCcw aria-hidden="true" size={15} /> {t("workbench.retry")}
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

function errorMessage(error: unknown, fallback = "The operation failed.") {
  return error instanceof Error ? error.message : fallback;
}
