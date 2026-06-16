import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import styles from "./ButtonLink.module.css";

type ButtonLinkProps = {
  children: ReactNode;
  to: string;
  variant?: "primary" | "secondary";
};

export function ButtonLink({
  children,
  to,
  variant = "secondary",
}: ButtonLinkProps) {
  return (
    <Link className={`${styles.button} ${styles[variant]}`} to={to}>
      {children}
    </Link>
  );
}
