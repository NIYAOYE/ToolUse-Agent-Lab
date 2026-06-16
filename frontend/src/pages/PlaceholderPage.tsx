import { useI18n } from "../i18n";
import styles from "./PlaceholderPage.module.css";

type PlaceholderPageProps = {
  title: string;
  description: string;
};

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  const { t } = useI18n();

  return (
    <section className={styles.page}>
      <div className={styles.coordinate}>{t("placeholder.coordinate")}</div>
      <h1>{title}</h1>
      <p>{description}</p>
      <div className={styles.rule} />
      <div className={styles.hold}>{t("placeholder.hold")}</div>
    </section>
  );
}
