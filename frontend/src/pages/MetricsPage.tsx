import { useQuery } from "@tanstack/react-query";

import { supportOpsApi } from "../lib/supportOpsApi";
import styles from "./OperationsViews.module.css";

export function MetricsPage() {
  const metrics = useQuery({
    queryKey: ["metrics", "diagnosis-time"],
    queryFn: () => supportOpsApi.diagnosisTimeMetrics(),
  });

  return (
    <section aria-labelledby="metrics-title" className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <span className={styles.coordinate}>METRIC / FIRST DIAGNOSIS</span>
          <h1 id="metrics-title">Diagnosis Time</h1>
          <p>
            Elapsed time from investigation start to the first structured
            diagnosis. This view does not measure approval or resolution time.
          </p>
        </div>
      </header>

      {metrics.isPending && <div className={styles.emptyState}>Loading metrics</div>}
      {metrics.isError && <div className={styles.error}>Metrics unavailable</div>}
      {metrics.data && (
        <div className={styles.metricsGrid}>
          <article className={styles.metric}>
            <span className={styles.metricLabel}>Diagnosed sample</span>
            <strong className={styles.metricValue}>{metrics.data.count}</strong>
            <p>{metrics.data.count} diagnosed tickets</p>
          </article>
          <article className={styles.metric}>
            <span className={styles.metricLabel}>Median</span>
            <strong className={styles.metricValue}>
              {formatSeconds(metrics.data.median_seconds)}
            </strong>
            <p>Half of first diagnoses completed at or below this duration.</p>
          </article>
          <article className={styles.metric}>
            <span className={styles.metricLabel}>P75</span>
            <strong className={styles.metricValue}>
              {formatSeconds(metrics.data.p75_seconds)}
            </strong>
            <p>Seventy-five percent completed at or below this duration.</p>
          </article>
        </div>
      )}
    </section>
  );
}

function formatSeconds(value: number | null) {
  return value === null ? "N/A" : `${value.toFixed(1)}s`;
}
