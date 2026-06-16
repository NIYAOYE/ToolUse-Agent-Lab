import {
  BarChart3,
  FilePlus2,
  ListFilter,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import styles from "./AppShell.module.css";

const navigation = [
  { to: "/tickets", label: "Tickets", index: "01", icon: ListFilter },
  { to: "/tickets/new", label: "New Ticket", index: "02", icon: FilePlus2 },
  { to: "/tickets/import", label: "Import", index: "03", icon: Upload },
  { to: "/metrics", label: "Metrics", index: "04", icon: BarChart3 },
] as const;

export function AppShell() {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <NavLink className={styles.brand} to="/tickets">
          <span aria-hidden="true" className={styles.brandMark} />
          <span>SUPPORTOPS</span>
        </NavLink>
        <div className={styles.networkStatus}>
          <span aria-hidden="true" className={styles.statusDot} />
          LOCAL / CONTROLLED NETWORK
        </div>
      </header>

      <nav aria-label="Primary navigation" className={styles.navigation}>
        <div className={styles.railLabel}>OPS / 2026</div>
        <div className={styles.navItems}>
          {navigation.map(({ to, label, index, icon: Icon }) => (
            <NavLink
              aria-label={label}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.navLinkActive : ""}`
              }
              end={to === "/tickets"}
              key={to}
              to={to}
            >
              <span className={styles.navIndex}>{index}</span>
              <Icon aria-hidden="true" size={18} strokeWidth={1.7} />
              <span>{label}</span>
            </NavLink>
          ))}
        </div>
        <div className={styles.reviewNote}>
          <ShieldCheck aria-hidden="true" size={20} strokeWidth={1.6} />
          <span>Human authority remains final.</span>
        </div>
      </nav>

      <main className={styles.content}>
        <Outlet />
      </main>

      <footer className={styles.footer}>
        <span>API CONNECTED</span>
        <span className={styles.footerRule} />
        <strong>HUMAN REVIEW REQUIRED</strong>
      </footer>
    </div>
  );
}
