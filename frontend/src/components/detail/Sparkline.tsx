interface SparklineProps {
  values: readonly number[];
  width?: number;
  height?: number;
  label: string;
}

/** A small hand-drawn SVG line. Lowest point gets a dot, since that is what people look for. */
export function Sparkline({ values, width = 240, height = 48, label }: SparklineProps) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pad = 4;
  const x = (i: number) => pad + (i / (values.length - 1)) * (width - pad * 2);
  const y = (v: number) => pad + (1 - (v - min) / span) * (height - pad * 2);
  const path = values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const lowIndex = values.indexOf(min);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      role="img"
      aria-label={label}
    >
      <path d={path} fill="none" stroke="var(--accent)" strokeWidth={1.8} vectorEffect="non-scaling-stroke" />
      <circle cx={x(lowIndex)} cy={y(min)} r={3} fill="var(--good)" />
    </svg>
  );
}
