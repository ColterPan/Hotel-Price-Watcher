// A bare "$" is ambiguous in an app whose whole point is SGD vs USD.
const DOLLAR_PREFIXES: Record<string, string> = {
  USD: "US$",
  SGD: "S$",
  AUD: "A$",
  NZD: "NZ$",
  CAD: "C$",
  HKD: "HK$",
  MXN: "MX$",
  MYR: "RM",
};

const WHOLE_NUMBER = new Intl.NumberFormat("en", { maximumFractionDigits: 0 });

/** "S$1,284", "US$98", "¥14,200". Whole units: nightly hotel prices never need cents. */
export function formatMoney(amount: number, currency: string): string {
  const prefix = DOLLAR_PREFIXES[currency];
  if (prefix) return `${prefix}${WHOLE_NUMBER.format(Math.round(amount))}`;
  try {
    return new Intl.NumberFormat("en", {
      style: "currency",
      currency,
      currencyDisplay: "narrowSymbol",
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    }).format(Math.round(amount));
  } catch {
    // Unknown currency code: still show something sensible.
    return `${currency} ${Math.round(amount).toLocaleString("en")}`;
  }
}

/** Parse a YYYY-MM-DD string as a local calendar date (not UTC midnight). */
export function parseDay(value: string): Date {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y ?? 1970, (m ?? 1) - 1, d ?? 1);
}

export function toDayString(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function addDays(date: Date, days: number): Date {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
}

export function nightsBetween(checkIn: string, checkOut: string): number {
  const ms = parseDay(checkOut).getTime() - parseDay(checkIn).getTime();
  return Math.round(ms / 86_400_000);
}

const SHORT_DATE = new Intl.DateTimeFormat("en", { day: "numeric", month: "short" });

/** "Nov 12 to Nov 14", kept short for the search bar and cards. */
export function formatStay(checkIn: string, checkOut: string): string {
  return `${SHORT_DATE.format(parseDay(checkIn))} to ${SHORT_DATE.format(parseDay(checkOut))}`;
}

export function formatShortDate(value: string): string {
  return SHORT_DATE.format(parseDay(value));
}

export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}

/** "just now", "5 min ago", "3 h ago", "2 days ago". */
export function timeAgo(iso: string, now: Date = new Date()): string {
  const seconds = Math.max(0, (now.getTime() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return plural(Math.floor(hours / 24), "day") + " ago";
}

export function formatReviews(count: number): string {
  if (count >= 10_000) return `${Math.round(count / 1000)}k reviews`;
  if (count >= 1_000) return `${(count / 1000).toFixed(1).replace(/\.0$/, "")}k reviews`;
  return plural(count, "review");
}
