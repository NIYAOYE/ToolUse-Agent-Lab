import type { InvestigationStatus, TicketStatus } from "../lib/contracts";
import { useI18n } from "../i18n";
import styles from "./StatusBadge.module.css";

type StatusBadgeProps = {
  status: InvestigationStatus | TicketStatus;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const { t } = useI18n();

  return (
    <span className={`${styles.badge} ${styles[status.toLowerCase()] ?? ""}`}>
      {t(`status.${status}`)}
    </span>
  );
}
