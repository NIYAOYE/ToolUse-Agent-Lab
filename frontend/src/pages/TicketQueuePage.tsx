import { ArrowUpRight, Upload } from "lucide-react";

import { ButtonLink } from "../components/ButtonLink";
import styles from "./TicketQueuePage.module.css";

const columns = ["Priority", "Ticket", "Service", "Status", "Updated"];

export function TicketQueuePage() {
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
          <span>NO LOCAL SAMPLE DATA</span>
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
              <tr>
                <td className={styles.emptyState} colSpan={columns.length}>
                  <span className={styles.emptyIndex}>000</span>
                  <strong>No ticket data loaded</strong>
                  <span>
                    The typed API boundary is ready for the Phase 6 queue.
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
