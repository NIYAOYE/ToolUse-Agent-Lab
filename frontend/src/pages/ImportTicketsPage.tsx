import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp, Upload } from "lucide-react";
import { useState } from "react";

import { useI18n } from "../i18n";
import { supportOpsApi } from "../lib/supportOpsApi";
import styles from "./OperationsViews.module.css";

export function ImportTicketsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const importTickets = useMutation({
    mutationFn: (selected: File) => supportOpsApi.importTickets(selected),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
  });

  return (
    <section aria-labelledby="import-title" className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <span className={styles.coordinate}>{t("import.coordinate")}</span>
          <h1 id="import-title">{t("import.title")}</h1>
          <p>{t("import.description")}</p>
        </div>
      </header>

      <div className={styles.importGrid}>
        <div className={styles.dropZone}>
          <FileUp aria-hidden="true" size={34} strokeWidth={1.5} />
          <label htmlFor="ticket-import">{t("import.fileLabel")}</label>
          <span className={styles.eyebrow}>{t("import.uploadEyebrow")}</span>
          <input
            accept=".csv,.json,text/csv,application/json"
            id="ticket-import"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            type="file"
          />
          <button
            className={styles.primaryButton}
            disabled={!file || importTickets.isPending}
            onClick={() => file && importTickets.mutate(file)}
            type="button"
          >
            <Upload aria-hidden="true" size={15} />
            {importTickets.isPending ? t("import.pending") : t("import.button")}
          </button>
          {importTickets.data && (
            <div className={styles.result} role="status">
              {importTickets.data.imported_count} {t("import.resultSuffix")}
            </div>
          )}
          {importTickets.isError && (
            <div className={styles.error} role="alert">
              {importTickets.error.message}
            </div>
          )}
        </div>

        <aside className={styles.panel}>
          <span className={styles.eyebrow}>{t("import.boundary")}</span>
          <ul className={styles.boundaryList}>
            <li>{t("import.boundaryFormats")}</li>
            <li>{t("import.boundaryFields")}</li>
            <li>{t("import.boundaryDuplicates")}</li>
            <li>{t("import.boundarySize")}</li>
            <li>{t("import.boundaryAuto")}</li>
          </ul>
        </aside>
      </div>
    </section>
  );
}
