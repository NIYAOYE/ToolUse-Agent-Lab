import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp, Upload } from "lucide-react";
import { useState } from "react";

import { supportOpsApi } from "../lib/supportOpsApi";
import styles from "./OperationsViews.module.css";

export function ImportTicketsPage() {
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
          <span className={styles.coordinate}>INTAKE / BATCH</span>
          <h1 id="import-title">Import Tickets</h1>
          <p>
            Submit one CSV or JSON file. Validation is atomic: invalid rows do
            not leave partial tickets behind.
          </p>
        </div>
      </header>

      <div className={styles.importGrid}>
        <div className={styles.dropZone}>
          <FileUp aria-hidden="true" size={34} strokeWidth={1.5} />
          <label htmlFor="ticket-import">CSV or JSON file</label>
          <span className={styles.eyebrow}>CONTROLLED MULTIPART UPLOAD</span>
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
            {importTickets.isPending ? "Importing..." : "Import tickets"}
          </button>
          {importTickets.data && (
            <div className={styles.result} role="status">
              {importTickets.data.imported_count} tickets imported
            </div>
          )}
          {importTickets.isError && (
            <div className={styles.error} role="alert">
              {importTickets.error.message}
            </div>
          )}
        </div>

        <aside className={styles.panel}>
          <span className={styles.eyebrow}>IMPORT BOUNDARY</span>
          <ul className={styles.boundaryList}>
            <li>Accepted formats: UTF-8 CSV and JSON.</li>
            <li>Required fields follow the ticket creation contract.</li>
            <li>Duplicate IDs and invalid rows reject the full batch.</li>
            <li>File-size limits are enforced by the backend.</li>
            <li>No investigation starts automatically after import.</li>
          </ul>
        </aside>
      </div>
    </section>
  );
}
