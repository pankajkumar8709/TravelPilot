/**
 * Design system — light + dark token sets, locked interest-tag colors,
 * type scale, spacing, and motion timings. One source of truth for every screen.
 */

// Locked accent color per interest tag (food=coral, culture=purple, outdoor=teal).
export const TAG_COLORS: Record<string, string> = {
  food: "#FF6B6B",
  culture: "#8E7CFF",
  outdoor: "#2DD4BF",
  nature: "#2DD4BF",
  history: "#F4A261",
  shopping: "#EC4899",
  nightlife: "#6366F1",
  hotel: "#334155",
};
export const tagColor = (tag: string) => TAG_COLORS[tag] ?? "#64748B";

export const TYPE = {
  display: { fontSize: 44, fontWeight: 800, lineHeight: 1.05, letterSpacing: "-0.02em" },
  h1: { fontSize: 30, fontWeight: 700, lineHeight: 1.15 },
  h2: { fontSize: 22, fontWeight: 700, lineHeight: 1.25 },
  h3: { fontSize: 17, fontWeight: 600, lineHeight: 1.3 },
  body: { fontSize: 14, fontWeight: 400, lineHeight: 1.55 },
  small: { fontSize: 12, fontWeight: 400, lineHeight: 1.4 },
} as const;

export const SP = { xs: 4, sm: 8, md: 16, lg: 24, xl: 40, xxl: 64 } as const;
export const RADIUS = 16;
export const ACCENT = "#2DD4BF";

// Motion timings (purposeful + fast: 150-300ms) and easings.
export const MOTION = {
  fast: 0.15,
  base: 0.24,
  slow: 0.35,
  ease: [0.22, 1, 0.36, 1] as [number, number, number, number], // easeOutExpo-ish
  spring: { type: "spring", stiffness: 380, damping: 30 } as const,
};

// Diff/state colors (mode-independent).
export const STATE = {
  added: "#22C55E",
  removed: "#EF4444",
  modified: "#F59E0B",
};

export type Mode = "light" | "dark";

export interface Palette {
  bg: string;
  bgElev: string;
  surface: string;
  surfaceAlt: string;
  border: string;
  text: string;
  textDim: string;
  accent: string;
  accentText: string;
  shadow: string;
}

export const PALETTES: Record<Mode, Palette> = {
  dark: {
    bg: "#0F1117",
    bgElev: "#151822",
    surface: "#181B24",
    surfaceAlt: "#212633",
    border: "#2A2F3D",
    text: "#E7EAF0",
    textDim: "#9AA3B2",
    accent: ACCENT,
    accentText: "#0F1117",
    shadow: "0 8px 30px rgba(0,0,0,0.45)",
  },
  light: {
    bg: "#F6F7F9",
    bgElev: "#FFFFFF",
    surface: "#FFFFFF",
    surfaceAlt: "#F1F3F6",
    border: "#E3E7ED",
    text: "#141821",
    textDim: "#5B6472",
    accent: "#0EA5A0",
    accentText: "#FFFFFF",
    shadow: "0 8px 30px rgba(20,30,50,0.10)",
  },
};

/**
 * Back-compat flat COLORS used by components not yet migrated to `palette`.
 * Defaults to the dark palette + state colors. New/rebuilt components should
 * read `palette` from useUI() instead so light mode works.
 */
export const COLORS = {
  ...PALETTES.dark,
  added: STATE.added,
  removed: STATE.removed,
  modified: STATE.modified,
} as const;
