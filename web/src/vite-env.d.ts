/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  /** Optional free CARTO key for native dark basemap tiles; OSM+CSS fallback without it. */
  readonly VITE_CARTO_API_KEY?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
