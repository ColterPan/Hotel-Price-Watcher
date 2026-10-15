import { useQuery } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { api } from "../api/client";
import { formatMoney } from "../lib/format";

const STORAGE_KEY = "hpw.currency";

interface MoneyContext {
  currency: string;
  setCurrency: (code: string) => void;
  supported: Record<string, string>;
  /** Show a USD amount in the chosen currency. Falls back to USD if rates are missing. */
  format: (usd: number) => string;
  /** Turn an amount typed in the chosen currency back into USD for the API. */
  toUsd: (amount: number) => number;
  ratesAsOf: string | null;
  ratesUnavailable: boolean;
}

const Ctx = createContext<MoneyContext | null>(null);

function readStored(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function store(code: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, code);
  } catch {
    // Private mode or blocked storage: the choice just won't survive a reload.
  }
}

interface CurrencyProviderProps {
  defaultCurrency: string;
  children: ReactNode;
}

export function CurrencyProvider({ defaultCurrency, children }: CurrencyProviderProps) {
  const [chosen, setChosen] = useState<string | null>(readStored);
  const rates = useQuery({
    queryKey: ["exchange-rates"],
    queryFn: api.exchangeRates,
    staleTime: 60 * 60 * 1000,
    retry: 1,
  });

  const currency = chosen ?? defaultCurrency;
  const rate = currency === "USD" ? 1 : Number(rates.data?.rates[currency] ?? NaN);
  const hasRate = Number.isFinite(rate) && rate > 0;

  const setCurrency = useCallback((code: string) => {
    setChosen(code);
    store(code);
  }, []);

  const value = useMemo<MoneyContext>(
    () => ({
      currency: hasRate ? currency : "USD",
      setCurrency,
      supported: rates.data?.supported_currencies ?? { USD: "US Dollar", [currency]: currency },
      format: (usd: number) => (hasRate ? formatMoney(usd * rate, currency) : formatMoney(usd, "USD")),
      toUsd: (amount: number) => (hasRate ? amount / rate : amount),
      ratesAsOf: rates.data?.as_of ?? null,
      ratesUnavailable: rates.isError,
    }),
    [currency, hasRate, rate, rates.data, rates.isError, setCurrency],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useMoney(): MoneyContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useMoney must be used inside CurrencyProvider");
  return ctx;
}
