import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SearchBar } from "./SearchBar";

function renderBar(initial: Parameters<typeof SearchBar>[0]["initial"] = null) {
  const onSearch = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <SearchBar initial={initial} onSearch={onSearch} busy={false} />
    </QueryClientProvider>,
  );
  return onSearch;
}

describe("SearchBar", () => {
  it("asks for a city before searching", async () => {
    const onSearch = renderBar();
    await userEvent.click(screen.getByRole("button", { name: /^search$/i }));
    expect(screen.getByRole("alert")).toHaveTextContent("Pick a city from the list first.");
    expect(onSearch).not.toHaveBeenCalled();
  });

  it("submits a complete search", async () => {
    const initial = {
      location_key: "g294265",
      location_name: "Singapore",
      check_in: "2030-01-10",
      check_out: "2030-01-12",
      adults: 2,
    };
    const onSearch = renderBar(initial);
    await userEvent.click(screen.getByRole("button", { name: "One more adult" }));
    await userEvent.click(screen.getByRole("button", { name: /^search$/i }));
    expect(onSearch).toHaveBeenCalledWith({ ...initial, adults: 3 });
  });
});
