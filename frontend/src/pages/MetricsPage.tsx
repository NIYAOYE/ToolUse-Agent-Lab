import { useQuery } from "@tanstack/react-query";

import { useI18n } from "../i18n";
import { supportOpsApi } from "../lib/supportOpsApi";
import styles from "./OperationsViews.module.css";

export function MetricsPage() {
  const { t } = useI18n();
  const metrics = useQuery({
    queryKey: ["metrics", "diagnosis-time"],
    queryFn: () => supportOpsApi.diagnosisTimeMetrics(),
  });

  return (
    <section aria-labelledby="metrics-title" className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <span className={styles.coordinate}>{t("metrics.coordinate")}</span>
          <h1 id="metrics-title">{t("metrics.title")}</h1>
          <p>{t("metrics.description")}</p>
        </div>
      </header>

      {metrics.isPending && (
        <div className={styles.emptyState}>{t("metrics.loading")}</div>
      )}
      {metrics.isError && <div className={styles.error}>{t("metrics.error")}</div>}
      {metrics.data && (
        <div className={styles.metricsGrid}>
          <article className={styles.metric}>
            <span className={styles.metricLabel}>{t("metrics.sample")}</span>
            <strong className={styles.metricValue}>{metrics.data.count}</strong>
            <p>{metrics.data.count} {t("metrics.sampleDetail")}</p>
          </article>
          <article className={styles.metric}>
            <span className={styles.metricLabel}>{t("metrics.median")}</span>
            <strong className={styles.metricValue}>
              {formatSeconds(metrics.data.median_seconds)}
            </strong>
            <p>{t("metrics.medianDetail")}</p>
          </article>
          <article className={styles.metric}>
            <span className={styles.metricLabel}>{t("metrics.p75")}</span>
            <strong className={styles.metricValue}>
              {formatSeconds(metrics.data.p75_seconds)}
            </strong>
            <p>{t("metrics.p75Detail")}</p>
          </article>
        </div>
      )}
    </section>
  );
}

function formatSeconds(value: number | null) {
  return value === null ? "N/A" : `${value.toFixed(1)}s`;
}
