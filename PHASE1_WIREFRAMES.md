# Phase 1 — Wireframe & Design-System Reference

The glanceable reference the plan's Phase 1 asks for: low-fidelity wireframes for
the four core screens + the locked design system. Anyone can read this and know
exactly what they're building toward. The tokens here are implemented verbatim in
`web/src/theme.ts`; the card pattern in `web/src/components/ActivityCard.tsx`.

---

## Design system (LOCKED — do not improvise)

### Interest-tag colors (one fixed accent per tag)
| Tag | Color | Hex |
|-----|-------|-----|
| food | coral | `#FF6B6B` |
| culture | purple | `#8E7CFF` |
| outdoor | teal | `#2DD4BF` |
| history | amber | `#F4A261` |
| shopping | pink | `#EC4899` |
| nightlife | indigo | `#6366F1` |
| hotel/stay | slate | `#334155` (fixed marker) |

Diff states: added `#22C55E` · removed `#EF4444` · modified `#F59E0B`.

### Type scale
| Role | Size | Weight |
|------|------|--------|
| h1 | 30 | 700 |
| h2 | 22 | 700 |
| h3 | 17 | 600 |
| body | 14 | 400 |
| small | 12 | 400 |

Spacing scale (px): 4 · 8 · 16 · 24 · 40. Radius: 12. Dark surface palette.

### The ONE activity-card pattern (reused on every screen)
```
┌────────────────────────────────────────────────┐
│ 09:00–10:30 │ Louvre Museum            [culture]│   ← left edge tinted by tag color
│             │ 90 min · €17                       │
└────────────────────────────────────────────────┘
```
Fields: time range · name · duration · cost · interest-tag chip. Never redesigned
per screen — the diff view just recolors the left edge (green/red/amber).

---

## Screen 1 — Setup form
```
┌──────────────────────────────────────────┐
│  Plan your Paris trip                      │  h1
│  A day-by-day itinerary that repairs...   │  body/dim
│                                            │
│  Dates      [ start ]  [ end ]             │
│  Budget     [====●======]  €400            │  slider
│  Interests  (culture)(history)(outdoor)    │  toggle chips, tag-colored
│             (food)(shopping)(nightlife)    │
│  Hotel      [ Hôtel du Louvre ▾ ]          │  select
│                                            │
│  [   Generate itinerary   ]                │  accent button
└──────────────────────────────────────────┘
```

## Screen 2 — Day view (one day, activities in sequence)
```
[Day 1][Day 2][Day 3]           ← day tabs
┌ activity card ┐  ⚡disrupt 🌧weather ✈flight
┌ activity card ┐  ⚡ 🌧 ✈
┌ activity card ┐  ⚡ 🌧 ✈
Suggestions:  🍽 <food> · lunch ~12-2pm   🛏 <stay> · tonight
```

## Screen 3 — Dashboard (full-trip summary, final deliverable)
Two columns:
```
LEFT  = day view (tabs + activity cards + inject buttons + suggestions)
RIGHT = map view (route polyline, numbered markers, hotel, suggestions, amenity toggle)
        + budget rollup (per-day + total, red if over)
        + diff view (appears when a disruption is pending)
        + NL ask box ("what should I do tomorrow morning?")
```

## Screen 4 — Diff view (before/after on disruption) — HIGHEST-LEVERAGE SCREEN
```
┌ [WEATHER DISRUPTION]  Day 1        87% plan-stable ┐
│ "Weather alert: 'Eiffel Tower' is outdoor —       │  plain-language reason
│  rebuilding the rest of the day around it."       │
│                                                    │
│ REMOVED   ┌ Eiffel Tower  09:00-10:30  [outdoor]┐ │  red edge, struck through
│ ADDED     ┌ Musée d'Orsay 09:15-11:15  [culture]┐ │  green edge
│ RESCHED   Louvre: 11:00-13:30 → 11:30-14:00        │  amber
│                                                    │
│ [ Confirm change ]   [ Reject ]                    │  confirm-before-apply
└────────────────────────────────────────────────────┘
```

---

## Exit criteria — ✅ MET
This doc is the shared reference. All four screens are sketched (diff view included),
the activity-card pattern is fixed, interest tags have locked colors, and the type
scale is written down — implemented in `web/src/theme.ts` + `web/src/components/`.
