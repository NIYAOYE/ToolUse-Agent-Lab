import { ArrowUpRight, Upload } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ButtonLink } from "../components/ButtonLink";
import { StatusBadge } from "../components/StatusBadge";
import { supportOpsApi } from "../lib/supportOpsApi";
import styles from "./TicketQueuePage.module.css";

const columns = ["Priority", "Ticket", "Service", "Status", "Updated"];

export function TicketQueuePage() {
  const tickets = useQuery({
    queryKey: ["tickets"],
    queryFn: () => supportOpsApi.listTickets(),
  });

  return (
    <section aria-labelledby="ticket-queue-title" className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <div className={styles.coordinate}>VIEW / 01</div>
          <h1 id="ticket-queue-title">Ticket Queue</h1>
          <p>
            Investigate incidents. Preserve evidence. Keep humans in control.
          </p>
        </div>
        <div className={styles.actions}>
          <ButtonLink to="/tickets/import">
            <Upload aria-hidden="true" size={16} />
            Import
          </ButtonLink>
          <ButtonLink to="/tickets/new" variant="primary">
            New ticket
            <ArrowUpRight aria-hidden="true" size={16} />
          </ButtonLink>
        </div>
      </header>

      <div className={styles.queueFrame}>
        <div className={styles.queueMeta}>
          <span>QUEUE / LIVE SOURCE</span>
          <span>
            {tickets.data ? `${tickets.data.total} RECORDS` : "CONNECTING"}
          </span>
        </div>
        <div className={styles.tableScroll}>
          <table>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column} scope="col">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tickets.isPending && (
                <QueueMessage
                  detail="Reading the SupportOps API."
                  title="Loading ticket queue"
                />
              )}
              {tickets.isError && (
                <QueueMessage
                  detail="Verify the local API and retry."
                  title="Ticket queue unavailable"
                />
              )}
              {tickets.data?.items.length === 0 && (
                <QueueMessage
                  detail="Create or import a ticket to begin."
                  title="No tickets to display"
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
      <td className={styles.emptyState} colSpan={columns.length}>
        <span className={styles.emptyIndex}>000</span>
        <strong>{title}</strong>
        <span>{detail}</span>
      </td>
    </tr>
  );
}
