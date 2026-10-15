import { describe, expect, it } from "vitest";

import { safeUrl } from "./safeUrl";

describe("safeUrl", () => {
  it("keeps http and https links", () => {
    expect(safeUrl("https://www.tripadvisor.com/Hotel_Review-g1-d2.html")).toBe(
      "https://www.tripadvisor.com/Hotel_Review-g1-d2.html",
    );
    expect(safeUrl("http://example.com/")).toBe("http://example.com/");
  });

  it.each(["javascript:alert(1)", "data:text/html,hi", "JAVASCRIPT:alert(1)", "not a url", "", null, undefined])(
    "drops %s",
    (value) => {
      expect(safeUrl(value)).toBeNull();
    },
  );
});
