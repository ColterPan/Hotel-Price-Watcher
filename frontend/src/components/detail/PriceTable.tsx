import { safeUrl } from "../../lib/safeUrl";
import type { Offer } from "../../types";
import styles from "./Detail.module.css";

interface PriceTableProps {
  offers: readonly Offer[];
  nights: number;
  formatPrice: (usd: number) => string;
  loading: boolean;
  failed: boolean;
}

export function PriceTable({ offers, nights, formatPrice, loading, failed }: PriceTableProps) {
  if (loading) {
    return (
      <div className={styles.tableSkeleton} aria-busy="true">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="skeleton" style={{ height: 34 }} />
        ))}
      </div>
    );
  }
  if (failed) {
    return <p className={styles.muted}>Couldn't load prices for these dates. Try again in a minute.</p>;
  }
  if (offers.length === 0) {
    return <p className={styles.muted}>No booking site has a price for these dates. It may be sold out.</p>;
  }

  const cheapest = Number(offers[0]!.nightly);
  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th scope="col">Site</th>
          <th scope="col" className={styles.right}>
            Per night
          </th>
          <th scope="col" className={styles.right}>
            {nights} {nights === 1 ? "night" : "nights"}
          </th>
        </tr>
      </thead>
      <tbody>
        {offers.map((offer) => {
          const nightly = Number(offer.nightly);
          const isCheapest = nightly === cheapest;
          const link = safeUrl(offer.link);
          return (
            <tr key={`${offer.site}-${offer.nightly}`} className={isCheapest ? styles.cheapestRow : undefined}>
              <td>
                {link ? (
                  <a href={link} target="_blank" rel="noopener noreferrer">
                    {offer.site}
                  </a>
                ) : (
                  offer.site
                )}
                {isCheapest ? <span className={styles.cheapestTag}>cheapest</span> : null}
                {offer.free_cancellation ? <span className={styles.freeCancel}>free cancellation</span> : null}
              </td>
              <td className={`num ${styles.right}`}>{formatPrice(nightly)}</td>
              <td className={`num ${styles.right} ${styles.mutedCell}`}>{formatPrice(nightly * nights)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
