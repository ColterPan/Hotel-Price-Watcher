import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { formatMoney } from "../../lib/format";
import type { HotelView } from "../../lib/view";
import type { Hotel } from "../../types";
import { HotelCard } from "./HotelCard";
import { ProviderStrip } from "./ProviderStrip";

const hotel: Hotel = {
  id: "g294265-d302294",
  name: "Pan Pacific Singapore",
  latitude: 1.29,
  longitude: 103.86,
  image_url: "javascript:alert(1)",
  url: null,
  accommodation_type: "Hotel",
  hotel_class: 5,
  amenities: [],
  labels: [],
  providers: ["xotelo"],
  rates_key: "g294265-d302294",
  ratings: [],
  offers: [],
  price: null,
  typical_min: "341",
  typical_max: "2502",
  typical_currency: "USD",
  quality: { score: 9.2, label: "Exceptional", review_count: 17055, low_confidence: false },
};

const sgd = (usd: number) => formatMoney(usd * 1.3, "SGD");

function renderCard(view: Partial<HotelView> = {}, onSelect = vi.fn()) {
  const full: HotelView = {
    hotel,
    price: { nightlyUsd: 306, kind: "live", site: "Trip.com" },
    value: { value: 0.85, grade: "A", qualityPct: 1, pricePct: 0.3 },
    loadingPrice: false,
    ...view,
  };
  render(
    <ul>
      <HotelCard view={full} nights={2} highlighted={false} formatPrice={sgd} onSelect={onSelect} onHover={() => {}} />
    </ul>,
  );
  return onSelect;
}

describe("HotelCard", () => {
  it("shows the live price in the display currency, the total, the site and the grade", () => {
    renderCard();
    expect(screen.getByText("Pan Pacific Singapore")).toBeInTheDocument();
    expect(screen.getByText("S$398")).toBeInTheDocument();
    expect(screen.getByText("S$796")).toBeInTheDocument();
    expect(screen.getByText(/on Trip.com/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Value A/)).toBeInTheDocument();
    expect(screen.getByText("9.2")).toBeInTheDocument();
    expect(screen.getByText("17k reviews")).toBeInTheDocument();
  });

  it("labels a typical price as a starting price while dated prices load", () => {
    renderCard({ price: { nightlyUsd: 341, kind: "typical", site: null }, loadingPrice: true });
    expect(screen.getByText("usually from")).toBeInTheDocument();
    expect(screen.getByText("checking your dates")).toBeInTheDocument();
  });

  it("never renders an unsafe image URL", () => {
    renderCard();
    expect(document.querySelector("img")).toBeNull();
  });

  it("selects the hotel on click", async () => {
    const onSelect = renderCard();
    await userEvent.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledWith("g294265-d302294");
  });
});

describe("ProviderStrip", () => {
  it("says plainly which sources worked and which did not", () => {
    render(
      <ProviderStrip
        statuses={{ xotelo: "ok", serpapi: "not_configured" }}
        diagnostics={{ serpapi: "SERPAPI_KEY is not set" }}
      />,
    );
    expect(screen.getByText("TripAdvisor prices: live")).toBeInTheDocument();
    expect(screen.getByText("Google Hotels: needs an API key")).toHaveAttribute("title", "SERPAPI_KEY is not set");
  });
});
