import { describe, expect, it } from "vitest";

import { estimatePillWidth, placePins } from "./collision";

describe("placePins", () => {
  it("shows every pill when none overlap", () => {
    const shown = placePins([
      { id: "a", x: 0, y: 0, width: 60 },
      { id: "b", x: 200, y: 0, width: 60 },
    ]);
    expect([...shown]).toEqual(["a", "b"]);
  });

  it("keeps the higher-priority pill when two collide", () => {
    const shown = placePins([
      { id: "best", x: 100, y: 100, width: 60 },
      { id: "worse", x: 120, y: 105, width: 60 },
      { id: "far", x: 400, y: 100, width: 60 },
    ]);
    expect(shown.has("best")).toBe(true);
    expect(shown.has("worse")).toBe(false);
    expect(shown.has("far")).toBe(true);
  });

  it("allows pills stacked with enough vertical room", () => {
    const shown = placePins([
      { id: "top", x: 100, y: 100, width: 60 },
      { id: "below", x: 100, y: 140, width: 60 },
    ]);
    expect(shown.size).toBe(2);
  });
});

describe("estimatePillWidth", () => {
  it("grows with the label", () => {
    expect(estimatePillWidth("S$1,284")).toBeGreaterThan(estimatePillWidth("S$98"));
  });
});
