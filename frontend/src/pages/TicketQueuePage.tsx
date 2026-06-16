import { ArrowUpRight, Upload } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ButtonLink } from "../components/ButtonLink";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";
import { supportOpsApi } from "../lib/supportOpsApi";
import styles from "./TicketQueuePage.module.css";

const columnKeys = [
  "tickets.priority",
  "tickets.ticket",
  "tickets.service",
  "tickets.status",
  "tickets.updated",
] as const;

export function TicketQueuePage() {
  const { t } = useI18n();
  const tickets = useQuery({
    queryKey: ["tickets"],
    queryFn: () => supportOpsApi.listTickets(),
  });

  return (
    <section aria-labelledby="ticket-queue-title" className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <div className={styles.coordinate}>{t("tickets.coordinate")}</div>
          <h1 id="ticket-queue-title">{t("tickets.title")}</h1>
          <p>{t("tickets.description")}</p>
        </div>
        <div className={styles.actions}>
          <ButtonLink to="/tickets/import">
            <Upload aria-hidden="true" size={16} />
            {t("tickets.import")}
          </ButtonLink>
          <ButtonLink to="/tickets/new" variant="primary">
            {t("tickets.newTicket")}
            <ArrowUpRight aria-hidden="true" size={16} />
          </ButtonLink>
        </div>
      </header>

      <div className={styles.queueFrame}>
        <div className={styles.queueMeta}>
          <span>{t("tickets.meta")}</span>
          <span>
            {tickets.data
              ? `${tickets.data.total} ${t("tickets.records")}`
              : t("tickets.connecting")}
          </span>
        </div>
        <div className={styles.tableScroll}>
          <table>
            <thead>
              <tr>
                {columnKeys.map((column) => (
                  <th key={column} scope="col">
                    {t(column)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tickets.isPending && (
                <QueueMessage
                  detail={t("tickets.loadingDetail")}
                  title={t("tickets.loadingTitle")}
                />
              )}
              {tickets.isError && (
                <QueueMessage
                  detail={t("tickets.errorDetail")}
                  title={t("tickets.errorTitle")}
                />
              )}
              {tickets.data?.items.length === 0 && (
                <QueueMessage
                  detail={t("tickets.emptyDetail")}
                  title={t("tickets.emptyTitle")}
                />
              )}
              {tickets.data?.items.map((ticket) => (
                <tr key={ticket.id}>
                  <td>
                    <strong className={styles.priority}>{ticket.priority}</strong>
                  </td>
                  <td>
                    <Link
                      aria-label={`Open ${ticket.id}`}
                      className={styles.ticketLink}
                      to={`/tickets/${encodeURIComponent(ticket.id)}`}
                    >
                      <span>{ticket.id}</span>
                      <strong>{ticket.title}</strong>
                    </Link>
                  </td>
                  <td>{ticket.service}</td>
                  <td>
                    <StatusBadge status={ticket.status} />
                  </td>
                  <td className={styles.updated}>
                    {new Intl.DateTimeFormat(undefined, {
                      month: "short",
                      day: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    }).format(new Date(ticket.updated_at))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function QueueMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <tr>
      <td className={styles.emptyState} colSpan={columnKeys.length}>
        <span className={styles.emptyIndex}>000</span>
        <strong>{title}</strong>
        <span>{detail}</span>
      </td>
    </tr>
  );
}
