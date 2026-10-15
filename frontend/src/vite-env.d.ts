/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Raster tile URL template for the map. Defaults to OpenStreetMap. */
  readonly VITE_TILE_URL?: string;
  /** HTML attribution for the tile provider. Required by most providers. */
  readonly VITE_TILE_ATTRIBUTION?: string;
  /** "false" to show tiles in their own colours instead of the dark filter. */
  readonly VITE_TILE_DARKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
