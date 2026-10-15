// Price pills overlap badly in dense city centres. This decides, for the
// current zoom, which pins get a full price pill and which shrink to a dot.
// Pins arrive in priority order (selected, hovered, best value first) and are
// placed greedily: a pill is shown only if it doesn't cover one already placed.

export interface PinBox {
  id: string;
  /** Centre of the pin in screen pixels. */
  x: number;
  y: number;
  width: number;
}

export const PILL_HEIGHT = 26;
const GAP = 3;

export function estimatePillWidth(label: string): number {
  // Geist Mono at 12px is about 7.2px per character, plus padding and border.
  return Math.round(label.length * 7.2 + 21);
}

export function placePins(pins: readonly PinBox[], height = PILL_HEIGHT): Set<string> {
  const placed: { left: number; right: number; top: number; bottom: number }[] = [];
  const shown = new Set<string>();
  for (const pin of pins) {
    const box = {
      left: pin.x - pin.width / 2 - GAP,
      right: pin.x + pin.width / 2 + GAP,
      top: pin.y - height / 2 - GAP,
      bottom: pin.y + height / 2 + GAP,
    };
    const overlaps = placed.some(
      (other) => box.left < other.right && box.right > other.left && box.top < other.bottom && box.bottom > other.top,
    );
    if (!overlaps) {
      placed.push(box);
      shown.add(pin.id);
    }
  }
  return shown;
}
