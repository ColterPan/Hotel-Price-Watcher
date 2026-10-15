import { PROVIDER_NAMES, STATUS_TEXT } from "../../lib/hotels";
import type { ProviderStatus } from "../../types";
import styles from "./Results.module.css";

interface ProviderStripProps {
  statuses: Record<string, ProviderStatus>;
  diagnostics: Record<string, string>;
}

/** Shows where results came from, and says plainly when a source failed. */
export function ProviderStrip({ statuses, diagnostics }: ProviderStripProps) {
  const entries = Object.entries(statuses);
  if (entries.length === 0) return null;
  return (
    <ul className={styles.providers} aria-label="Data sources">
      {entries.map(([name, status]) => (
        <li key={name} className={styles.provider} data-status={status} title={diagnostics[name] ?? undefined}>
          <span className={styles.providerDot} aria-hidden="true" />
          {PROVIDER_NAMES[name] ?? name}: {name === "demo" && status === "ok" ? "made-up prices" : STATUS_TEXT[status]}
        </li>
      ))}
    </ul>
  );
}
