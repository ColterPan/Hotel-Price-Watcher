import type { Grade } from "../../lib/value";
import type { QualityScore } from "../../types";
import styles from "./Results.module.css";

export function ScoreBadge({ quality, size = "md" }: { quality: QualityScore | null; size?: "md" | "lg" }) {
  if (!quality) {
    return <span className={`${styles.score} ${styles.scoreNone}`}>No reviews</span>;
  }
  return (
    <span
      className={`${styles.score} ${size === "lg" ? styles.scoreLg : ""}`}
      title={quality.low_confidence ? "Based on very few reviews" : `${quality.label}, adjusted for review count`}
    >
      <span className={`num ${styles.scoreValue}`}>{quality.score.toFixed(1)}</span>
      <span>{quality.label}</span>
      {quality.low_confidence ? <span className={styles.scoreWarn}>few reviews</span> : null}
    </span>
  );
}

const GRADE_HINT: Record<Grade, string> = {
  A: "Great value for this area",
  B: "Good value",
  C: "Fair value",
  D: "Pricey for what you get",
  E: "Poor value here",
};

export function GradeBadge({ grade }: { grade: Grade | null }) {
  if (!grade) return null;
  return (
    <span className={styles.grade} data-grade={grade} title={GRADE_HINT[grade]} aria-label={`Value ${grade}: ${GRADE_HINT[grade]}`}>
      {grade}
    </span>
  );
}
