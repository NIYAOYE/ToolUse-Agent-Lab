import styles from "./PlaceholderPage.module.css";

type PlaceholderPageProps = {
  title: string;
  description: string;
};

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <section className={styles.page}>
      <div className={styles.coordinate}>ROUTE / FOUNDATION</div>
      <h1>{title}</h1>
      <p>{description}</p>
      <div className={styles.rule} />
      <div className={styles.hold}>INTERFACE RESERVED</div>
    </section>
  );
}
