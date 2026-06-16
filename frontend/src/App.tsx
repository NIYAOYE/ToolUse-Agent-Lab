import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { I18nProvider, useI18n } from "./i18n";
import { InvestigationWorkbenchPage } from "./pages/InvestigationWorkbenchPage";
import { AuditPage } from "./pages/AuditPage";
import { ImportTicketsPage } from "./pages/ImportTicketsPage";
import { MetricsPage } from "./pages/MetricsPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { TicketQueuePage } from "./pages/TicketQueuePage";

export function App() {
  return (
    <I18nProvider>
      <LocalizedRoutes />
    </I18nProvider>
  );
}

function LocalizedRoutes() {
  const { t } = useI18n();

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate replace to="/tickets" />} />
        <Route path="tickets" element={<TicketQueuePage />} />
        <Route
          path="tickets/new"
          element={
            <PlaceholderPage
              title={t("placeholder.createTitle")}
              description={t("placeholder.createDescription")}
            />
          }
        />
        <Route path="tickets/import" element={<ImportTicketsPage />} />
        <Route
          path="tickets/:ticketId"
          element={<InvestigationWorkbenchPage />}
        />
        <Route path="metrics" element={<MetricsPage />} />
        <Route path="audits/:investigationId" element={<AuditPage />} />
        <Route path="*" element={<Navigate replace to="/tickets" />} />
      </Route>
    </Routes>
  );
}
