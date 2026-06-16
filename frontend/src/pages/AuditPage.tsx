import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";
import { supportOpsApi } from "../lib/supportOpsApi";
import styles from "./OperationsViews.module.css";

export function AuditPage() {
  const { t } = useI18n();
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
    return <div className={styles.error}>{t("audit.invalid")}</div>;
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
            <ArrowLeft aria-hidden="true" size={14} /> {t("audit.back")}
          </Link>
          <span className={styles.coordinate}>
            {t("audit.coordinate")} / {investigationId}
          </span>
          <h1 id="audit-title">{t("audit.title")}</h1>
          <p>{t("audit.description")}</p>
        </div>
      </header>

      {(detail.isPending || audits.isPending) && (
        <div className={styles.emptyState}>{t("audit.loading")}</div>
      )}
      {(detail.isError || audits.isError) && (
        <div className={styles.error}>{t("audit.error")}</div>
      )}
      {detail.data && audits.data && (
        <div className={styles.auditGrid}>
          <aside className={`${styles.panel} ${styles.auditSummary}`}>
            <span className={styles.eyebrow}>{t("audit.record")}</span>
            <dl className={styles.facts}>
              <div><dt>{t("audit.ticket")}</dt><dd>{detail.data.investigation.ticket_id}</dd></div>
              <div><dt>{t("audit.session")}</dt><dd>{detail.data.investigation.session_id}</dd></div>
              <div><dt>{t("audit.status")}</dt><dd><StatusBadge status={detail.data.investigation.status} /></dd></div>
              <div><dt>{t("audit.events")}</dt><dd>{detail.data.events.length}</dd></div>
              <div><dt>{t("audit.evidence")}</dt><dd>{detail.data.evidence.length}</dd></div>
              <div><dt>{t("audit.decisions")}</dt><dd>{detail.data.approvals.length}</dd></div>
              <div><dt>{t("audit.toolCalls")}</dt><dd>{audits.data.length}</dd></div>
            </dl>
          </aside>

          <div className={styles.auditList}>
            {audits.data.length === 0 && (
              <div className={styles.emptyState}>{t("audit.noTools")}</div>
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
                    <span className={styles.fieldLabel}>{t("audit.arguments")}</span>
                    <pre>{JSON.stringify(audit.arguments, null, 2)}</pre>
                  </section>
                  <section>
                    <span className={styles.fieldLabel}>{t("audit.result")}</span>
                    <pre>{JSON.stringify(audit.result, null, 2)}</pre>
                  </section>
                </div>
              </article>
            ))}

            <section className={styles.ledger}>
              <h2>{t("audit.investigationEvents")}</h2>
              {detail.data.events.length === 0 && <p>{t("audit.noEvents")}</p>}
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
              <h2>{t("audit.evidenceLedger")}</h2>
              {detail.data.evidence.length === 0 && <p>{t("audit.noEvidence")}</p>}
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
              <h2>{t("audit.humanDecisions")}</h2>
              {detail.data.approvals.length === 0 && <p>{t("audit.noDecisions")}</p>}
              {detail.data.approvals.map((approval) => (
                <article className={styles.ledgerItem} key={approval.id}>
                  <header>
                    <strong>{approval.decision}</strong>
                    <time>{formatDate(approval.created_at)}</time>
                  </header>
                  <span className={styles.fieldLabel}>{t("audit.reviewNotes")}</span>
                  <p>{approval.review_notes || t("audit.noReviewNotes")}</p>
                  <span className={styles.fieldLabel}>{t("audit.finalDraft")}</span>
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
