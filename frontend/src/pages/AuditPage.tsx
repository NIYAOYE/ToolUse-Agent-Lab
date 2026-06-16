import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../components/StatusBadge";
import { supportOpsApi } from "../lib/supportOpsApi";
import styles from "./OperationsViews.module.css";

export function AuditPage() {
  const { investigationId = "" } = useParams();
  const parsedId = Number(investigationId);
  const enabled = Number.isInteger(parsedId) && parsedId > 0;
  const detail = useQuery({
    queryKey: ["investigation", parsedId],
    queryFn: () => supportOpsApi.getInvestigation(parsedId),
    enabled,
  });
  const audits = useQuery({
    queryKey: ["investigation", parsedId, "audits"],
    queryFn: () => supportOpsApi.listInvestigationAudits(parsedId),
    enabled,
  });

  if (!enabled) {
    return <div className={styles.error}>Invalid investigation ID.</div>;
  }

  return (
    <section aria-labelledby="audit-title" className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <Link
            className={styles.backLink}
            to={
              detail.data
                ? `/tickets/${encodeURIComponent(detail.data.investigation.ticket_id)}`
                : "/tickets"
            }
          >
            <ArrowLeft aria-hidden="true" size={14} /> Back to workbench
          </Link>
          <span className={styles.coordinate}>AUDIT / {investigationId}</span>
          <h1 id="audit-title">Investigation Audit</h1>
          <p>
            Read-only trace of tool inputs, outputs, evidence, events, and human
            decisions for this investigation.
          </p>
        </div>
      </header>

      {(detail.isPending || audits.isPending) && (
        <div className={styles.emptyState}>Loading audit trace</div>
      )}
      {(detail.isError || audits.isError) && (
        <div className={styles.error}>Audit trace unavailable</div>
      )}
      {detail.data && audits.data && (
        <div className={styles.auditGrid}>
          <aside className={`${styles.panel} ${styles.auditSummary}`}>
            <span className={styles.eyebrow}>INVESTIGATION RECORD</span>
            <dl className={styles.facts}>
              <div><dt>Ticket</dt><dd>{detail.data.investigation.ticket_id}</dd></div>
              <div><dt>Session</dt><dd>{detail.data.investigation.session_id}</dd></div>
              <div><dt>Status</dt><dd><StatusBadge status={detail.data.investigation.status} /></dd></div>
              <div><dt>Events</dt><dd>{detail.data.events.length}</dd></div>
              <div><dt>Evidence</dt><dd>{detail.data.evidence.length}</dd></div>
              <div><dt>Decisions</dt><dd>{detail.data.approvals.length}</dd></div>
              <div><dt>Tool calls</dt><dd>{audits.data.length}</dd></div>
            </dl>
          </aside>

          <div className={styles.auditList}>
            {audits.data.length === 0 && (
              <div className={styles.emptyState}>No tool calls were recorded.</div>
            )}
            {audits.data.map((audit, index) => (
              <article className={styles.auditRecord} key={audit.id}>
                <header>
                  <h2>{audit.tool_name}</h2>
                  <span className={styles.recordMeta}>
                    {String(index + 1).padStart(2, "0")} / {audit.call_id}
                  </span>
                </header>
                <div className={styles.auditRecordBody}>
                  <section>
                    <span className={styles.fieldLabel}>Arguments</span>
                    <pre>{JSON.stringify(audit.arguments, null, 2)}</pre>
                  </section>
                  <section>
                    <span className={styles.fieldLabel}>Result</span>
                    <pre>{JSON.stringify(audit.result, null, 2)}</pre>
                  </section>
                </div>
              </article>
            ))}

            <section className={styles.ledger}>
              <h2>Investigation events</h2>
              {detail.data.events.length === 0 && <p>No events recorded.</p>}
              {detail.data.events.map((event) => (
                <article className={styles.ledgerItem} key={event.id}>
                  <header>
                    <strong>{formatEvent(event.event)}</strong>
                    <time>{formatDate(event.created_at)}</time>
                  </header>
                  <pre>{JSON.stringify(event.payload, null, 2)}</pre>
                </article>
              ))}
            </section>

            <section className={styles.ledger}>
              <h2>Evidence ledger</h2>
              {detail.data.evidence.length === 0 && <p>No evidence recorded.</p>}
              {detail.data.evidence.map((evidence) => (
                <article className={styles.ledgerItem} key={evidence.id}>
                  <header>
                    <strong>{evidence.title}</strong>
                    <span>{evidence.kind}</span>
                  </header>
                  <p>{evidence.summary}</p>
                  {evidence.source_ref && <code>{evidence.source_ref}</code>}
                </article>
              ))}
            </section>

            <section className={styles.ledger}>
              <h2>Human decisions</h2>
              {detail.data.approvals.length === 0 && <p>No decisions recorded.</p>}
              {detail.data.approvals.map((approval) => (
                <article className={styles.ledgerItem} key={approval.id}>
                  <header>
                    <strong>{approval.decision}</strong>
                    <time>{formatDate(approval.created_at)}</time>
                  </header>
                  <span className={styles.fieldLabel}>Review notes</span>
                  <p>{approval.review_notes || "No review notes."}</p>
                  <span className={styles.fieldLabel}>Final draft</span>
                  <pre>{approval.final_draft}</pre>
                </article>
              ))}
            </section>
          </div>
        </div>
      )}
    </section>
  );
}

function formatEvent(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
