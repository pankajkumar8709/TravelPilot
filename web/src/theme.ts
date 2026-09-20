/**
 * TravelPilot design system — "the journey is the interface."
 *
 * Palette: ink-and-harbor. Cloud is the page; Harbor is the only interactive
 * color; Beacon is reserved strictly for money/urgency (book links, price
 * highlights, diff confirm). Interest-tag colors are a separate family so a
 * tag never reads as a button.
 *
 * Type: Instrument Sans (display/UI) + Newsreader (narrative, italic for
 * emphasis). Narrative voice is reserved for descriptive prose — place
 * descriptions, assistant messages, empty states — never labels or buttons.
 */

export const INK = "#10151F";
export const CLOUD = "#F1F3F0";
export const HARBOR = "#1F6F78";
export const BEACON = "#E8963D";
export const SLATE = "#4B5563";

/** Interactive accent aliases — Harbor, kept so existing call sites stay valid. */
export const ACCENT = HARBOR;

/** Interest-tag palette (distinct from the functional accents above). */
export const TAG_COLORS: Record<string, string> = {
  food: "#D64550",
  culture: "#7C5CBF",
  nature: "#4C9A56",
  outdoor: "#4C9A56",
  nightlife: "#3457D5",
  shopping: "#A6763A",
  history: "#A6763A",
  other: "#A6763A",
  hotel: INK,
};
export const tagColor = (tag: string) => TAG_COLORS[tag] ?? TAG_COLORS.other;

export const FONT = {
  display: "'Instrument Sans', 'General Sans', 'Neue Montreal', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  narrative: "'Newsreader', Georgia, 'Times New Roman', serif",
} as const;

/**
 * Type scale (base 16px). Display/UI = Instrument Sans; narrative styles set
 * the Newsreader stack and italic weight where the guide asks for emphasis.
 */
export const TYPE = {
  display: { fontFamily: FONT.display, fontSize: 52, fontWeight: 500, lineHeight: 1.08, letterSpacing: "-0.01em" },
  h1: { fontFamily: FONT.display, fontSize: 28, fontWeight: 500, lineHeight: 1.2 },
  h2: { fontFamily: FONT.display, fontSize: 22, fontWeight: 500, lineHeight: 1.25 },
  h3: { fontFamily: FONT.display, fontSize: 18, fontWeight: 500, lineHeight: 1.3 },
  cardTitle: { fontFamily: FONT.display, fontSize: 18, fontWeight: 500, lineHeight: 1.3 },
  /** Narrative prose — Newsreader regular, 16/1.6. */
  body: { fontFamily: FONT.narrative, fontSize: 16, fontWeight: 400, lineHeight: 1.6 },
  /** Narrative emphasized — Newsreader italic (assistant voice, descriptions). */
  narrative: { fontFamily: FONT.narrative, fontSize: 16, fontWeight: 400, fontStyle: "italic" as const, lineHeight: 1.6 },
  /** UI labels, timestamps, meta — 13px Instrument Sans. Never all-caps. */
  small: { fontFamily: FONT.display, fontSize: 13, fontWeight: 400, lineHeight: 1.45 },
} as const;

export const SP = { xs: 4, sm: 8, md: 16, lg: 24, xl: 40, xxl: 64 } as const;

/** Card radii: activity 12, suggestion 8 — deliberately different (guide). */
export const RADIUS = 12;
export const RADIUS_SUGGESTION = 8;

/** Motion timings (response motion only; generation moment is in motion.ts). */
export const MOTION = {
  fast: 0.15,
  base: 0.2,   // chat panel expand/collapse (200ms, per guide)
  slow: 0.35,
  ease: [0.22, 1, 0.36, 1] as [number, number, number, number],
  spring: { type: "spring", stiffness: 380, damping: 30 } as const,
};

/** Diff/state colors (mode-independent). Text labels always accompany them. */
export const STATE = {
  added: "#22C55E",
  removed: "#EF4444",
  modified: BEACON,
};

export type Mode = "light" | "dark";

export interface Palette {
  bg: string;          // page background (Cloud in light, Ink in dark)
  bgElev: string;
  surface: string;     // card surface
  surfaceAlt: string;
  border: string;
  text: string;        // primary text
  textDim: string;     // secondary text (Slate family)
  accent: string;      // Harbor in both modes
  accentText: string;
  beacon: string;      // money/urgency accent (same both modes)
  shadow: string;
}

export const PALETTES: Record<Mode, Palette> = {
  dark: {
    bg: INK,
    bgElev: "#171D29",
    surface: "#FFFFFF0F", // ivory line — white at low opacity over Ink
    surfaceAlt: "#FFFFFF14",
    border: "#FFFFFF1F",
    text: "#F1F3F0",
    textDim: "#9CA5B4",
    accent: HARBOR,
    accentText: "#F1F3F0",
    beacon: BEACON,
    shadow: "0 8px 30px rgba(0,0,0,0.45)",
  },
  light: {
    bg: CLOUD,
    bgElev: "#FFFFFF",
    surface: "#FFFFFF",
    surfaceAlt: "#E7EAE6",
    border: "#D6DBD6",
    text: INK,
    textDim: SLATE,
    accent: HARBOR,
    accentText: "#F1F3F0",
    beacon: BEACON,
    shadow: "0 6px 24px rgba(16,21,31,0.08)",
  },
};

/**
 * Back-compat flat COLORS (dark palette + state colors) for components not yet
 * on `palette`. New code should read `palette` from useUI().
 */
export const COLORS = {
  ...PALETTES.dark,
  added: STATE.added,
  removed: STATE.removed,
  modified: STATE.modified,
} as const;
