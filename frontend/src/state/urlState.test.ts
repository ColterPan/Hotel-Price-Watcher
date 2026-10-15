import { describe, expect, it } from "vitest";

import { readSearchFromUrl } from "./urlState";

describe("readSearchFromUrl", () => {
  it("reads a complete search", () => {
    expect(readSearchFromUrl("?loc=g294265&name=Singapore&in=2026-11-20&out=2026-11-22&adults=3")).toEqual({
      location_key: "g294265",
      location_name: "Singapore",
      check_in: "2026-11-20",
      check_out: "2026-11-22",
      adults: 3,
    });
  });

  it.each([
    "?name=Singapore&in=2026-11-20&out=2026-11-22",
    "?loc=singapore&name=Singapore&in=2026-11-20&out=2026-11-22",
    "?loc=g294265&name=Singapore&in=tomorrow&out=2026-11-22",
    "?loc=g294265&name=Singapore&in=2026-11-20&out=2026-11-22&adults=40",
  ])("rejects incomplete or tampered input %s", (search) => {
    expect(readSearchFromUrl(search)).toBeNull();
  });
});
