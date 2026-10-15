/**
 * Links and images come from third-party APIs. Only plain http(s) URLs are
 * rendered, so a hostile or broken response can never inject "javascript:"
 * or "data:" URLs into the page.
 */
export function safeUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : null;
  } catch {
    return null;
  }
}
