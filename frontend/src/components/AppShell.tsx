import {
  BarChart3,
  FilePlus2,
  ListFilter,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useI18n } from "../i18n";
import styles from "./AppShell.module.css";

const navigation = [
  { to: "/tickets", labelKey: "shell.tickets", index: "01", icon: ListFilter },
  {
    to: "/tickets/new",
    labelKey: "shell.newTicket",
    index: "02",
    icon: FilePlus2,
  },
  { to: "/tickets/import", labelKey: "shell.import", index: "03", icon: Upload },
  { to: "/metrics", labelKey: "shell.metrics", index: "04", icon: BarChart3 },
] as const;

export function AppShell() {
  const { language, setLanguage, t } = useI18n();

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <NavLink className={styles.brand} to="/tickets">
          <span aria-hidden="true" className={styles.brandMark} />
          <span>SUPPORTOPS</span>
        </NavLink>
        <div className={styles.headerTools}>
          <div className={styles.languageSwitch} aria-label={t("language.label")}>
            <button
              aria-pressed={language === "en"}
              className={language === "en" ? styles.languageActive : ""}
              onClick={() => setLanguage("en")}
              type="button"
            >
              {t("language.english")}
            </button>
            <button
              aria-pressed={language === "zh"}
              className={language === "zh" ? styles.languageActive : ""}
              onClick={() => setLanguage("zh")}
              type="button"
            >
              {t("language.chinese")}
            </button>
          </div>
          <div className={styles.networkStatus}>
            <span aria-hidden="true" className={styles.statusDot} />
            {t("shell.network")}
          </div>
        </div>
      </header>

      <nav aria-label={t("shell.navLabel")} className={styles.navigation}>
        <div className={styles.railLabel}>OPS / 2026</div>
        <div className={styles.navItems}>
          {navigation.map(({ to, labelKey, index, icon: Icon }) => {
            const label = t(labelKey);
            return (
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
          );
          })}
        </div>
        <div className={styles.reviewNote}>
          <ShieldCheck aria-hidden="true" size={20} strokeWidth={1.6} />
          <span>{t("shell.reviewNote")}</span>
        </div>
      </nav>

      <main className={styles.content}>
        <Outlet />
      </main>

      <footer className={styles.footer}>
        <span>{t("shell.apiConnected")}</span>
        <span className={styles.footerRule} />
        <strong>{t("shell.humanReview")}</strong>
      </footer>
    </div>
  );
}
