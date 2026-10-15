import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LocationField } from "./LocationField";

const CITIES = [
  { name: "Singapore", country: "Singapore", location_key: "g294265", latitude: 1.29, longitude: 103.8 },
  { name: "Kuala Lumpur", country: "Malaysia", location_key: "g298570", latitude: 3.1, longitude: 101.7 },
];

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("LocationField", () => {
  it("typing fast and pressing Enter picks a match for what was typed, not a stale suggestion", async () => {
    // The server filters by the query, like the real /api/locations.
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const q = new URL(url, "http://x").searchParams.get("q")?.toLowerCase() ?? "";
        const matches = CITIES.filter((c) => c.name.toLowerCase().startsWith(q));
        return new Response(JSON.stringify(matches), { status: 200 });
      }),
    );
    const onChange = vi.fn();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <LocationField value={null} onChange={onChange} />
      </QueryClientProvider>,
    );

    const input = screen.getByRole("combobox");
    await userEvent.click(input);
    // Default list (Singapore first) is showing; type and hit Enter before it refreshes.
    await userEvent.type(input, "kual{Enter}", { delay: 1 });

    await waitFor(() => expect(onChange).toHaveBeenCalledWith({ key: "g298570", name: "Kuala Lumpur" }));
    expect(onChange).not.toHaveBeenCalledWith({ key: "g294265", name: "Singapore" });
  });
});
