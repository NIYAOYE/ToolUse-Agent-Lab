import type { InvestigationStatus, TicketStatus } from "../lib/contracts";
import styles from "./StatusBadge.module.css";

type StatusBadgeProps = {
  status: InvestigationStatus | TicketStatus;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[status.toLowerCase()] ?? ""}`}>
      {status}
    </span>
  );
}
