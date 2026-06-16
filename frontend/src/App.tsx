import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { TicketQueuePage } from "./pages/TicketQueuePage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate replace to="/tickets" />} />
        <Route path="tickets" element={<TicketQueuePage />} />
        <Route
          path="tickets/new"
          element={
            <PlaceholderPage
              title="Create Ticket"
              description="Manual ticket intake route is ready for the Phase 6 workflow."
            />
          }
        />
        <Route
          path="tickets/import"
          element={
            <PlaceholderPage
              title="Import Tickets"
              description="CSV and JSON import UI will connect to the existing intake API."
            />
          }
        />
        <Route
          path="tickets/:ticketId"
          element={
            <PlaceholderPage
              title="Ticket Detail"
              description="The shareable investigation view is reserved for Phase 6."
            />
          }
        />
        <Route
          path="metrics"
          element={
            <PlaceholderPage
              title="Diagnosis Metrics"
              description="Median and P75 diagnosis-time views arrive in Phase 7."
            />
          }
        />
        <Route
          path="audits/:investigationId"
          element={
            <PlaceholderPage
              title="Investigation Audit"
              description="Full tool and evidence audit detail arrives in Phase 7."
            />
          }
        />
        <Route path="*" element={<Navigate replace to="/tickets" />} />
      </Route>
    </Routes>
  );
}
