import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Compass, Printer, Share2, CloudRain } from "lucide-react";
import { api, type Amenity, type Change, type DayRoute, type Place, type Trip } from "../api";
import { SP, TYPE, RADIUS, MOTION, FONT } from "../theme";
import { useUI } from "../ui-context";
import { currencySymbol, t } from "../i18n";
import { SortableDayView } from "./SortableDayView";
import { MapView } from "./MapView";
import { DiffView } from "./DiffView";
import { ChatPanel } from "./ChatPanel";
import { SuggestionCard } from "./ActivityCard";
import { ActivityCardSkeleton } from "./Skeleton";

/** Screen 3 — the itinerary. Journey-spine day view / dark map toggle + budget rail. */
export function Dashboard({ tripId, onReset }: { tripId: number; onReset: () => void }) {
  const { palette, lang, currency, setCurrency } = useUI();
  const sym = currencySymbol(currency);
  const [trip, setTrip] = useState<Trip | null>(null);
  const [places, setPlaces] = useState<Place[]>([]);
  const [amenities, setAmenities] = useState<Amenity[]>([]);
  const [budget, setBudget] = useState<{ per_day: { day_index: number; cost: number }[]; total: number; budget_total: number; over_budget: boolean } | null>(null);
  const [activeDay, setActiveDay] = useState(1);
  const [view, setView] = useState<"list" | "map">("list");
  const [change, setChange] = useState<Change | null>(null);
  const [dayRoute, setDayRoute] = useState<DayRoute | null>(null);
  const [busy, setBusy] = useState(false);
  const [highlightIds, setHighlightIds] = useState<number[]>([]);
  const [shareMsg, setShareMsg] = useState("");
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      const td = await api.getTrip(tripId);
      setTrip(td);
      setCurrency(td.currency || "INR");
      setBudget(await api.budget(tripId));
      setChange(td.pending_changes[0] ?? null);
      setError("");
    } catch (e) {
      setError("Couldn't reach the planner — check your connection and try again.");
    }
  };

  const reorder = async (orderedPlaceIds: number[]) => {
    setBusy(true);
    try { setChange(await api.chatReorder({ trip_id: tripId, day_index: activeDay, ordered_place_ids: orderedPlaceIds })); }
    finally { setBusy(false); }
  };

  const share = async () => {
    try {
      const s = await api.share(tripId);
      const url = `${window.location.origin}/?trip=${s.share_id}`;
      await navigator.clipboard.writeText(url).catch(() => {});
      setShareMsg(t("share_copied", lang));
      setTimeout(() => setShareMsg(""), 2000);
    } catch { setShareMsg("Couldn't copy the link — try again in a moment."); setTimeout(() => setShareMsg(""), 2000); }
  };

  // Re-pull cached places when the trip's city changes (chat destination change
  // re-ingests a new city, so the old cache is stale).
  const tripCity = trip?.city;
  useEffect(() => {
    api.places().then(setPlaces);
    api.amenities().then(setAmenities);
  }, [tripCity]);

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tripId]);

  const hotel = useMemo(() => places.find((p) => p.id === trip?.hotel_place_id) ?? null, [places, trip]);
  const day = trip?.days.find((d) => d.day_index === activeDay) ?? null;

  // Route geometry loads when the map view (or day) is shown; cached server-side.
  useEffect(() => {
    if (view !== "map") return;
    let alive = true;
    setDayRoute(null);
    api.dayRoute(tripId, activeDay).then((r) => alive && setDayRoute(r)).catch(() => alive && setDayRoute(null));
    return () => { alive = false; };
  }, [tripId, activeDay, view]);

  const inject = async (placeId: number, trigger: string) => {
    setBusy(true);
    try { setChange(await api.inject({ trip_id: tripId, day_index: activeDay, disrupted_place_id: placeId, trigger })); }
    finally { setBusy(false); }
  };
  const applyChange = async (ch: Change) => {
    await api.confirm(tripId, ch.id);
    const added = (ch.diff.added || []).map((a) => a.place_id);
    if (ch.diff.day_index) setActiveDay(ch.diff.day_index);
    await refresh();
    setHighlightIds(added);
    setTimeout(() => setHighlightIds([]), 1400);
  };
  const confirm = async () => {
    if (!change) return;
    setBusy(true);
    try { await applyChange(change); setChange(null); }
    finally { setBusy(false); }
  };
  const reject = async () => {
    if (!change) return;
    setBusy(true);
    try { await api.reject(tripId, change.id); setChange(null); await refresh(); }
    finally { setBusy(false); }
  };

  if (error) {
    return (
      <div style={{ maxWidth: 460, margin: "10vh auto 0", textAlign: "left", display: "grid", gap: SP.md,
                    background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: RADIUS, padding: SP.xl }}>
        <Compass size={32} strokeWidth={1.6} color={palette.accent} />
        <div style={{ ...TYPE.h3, color: palette.text }}>Couldn't load this trip</div>
        <div style={{ ...TYPE.narrative, color: palette.textDim }}>{error}</div>
        <button onClick={refresh} style={{ ...TYPE.h3, fontSize: 15, minHeight: 44, justifySelf: "start",
                 padding: "10px 24px", borderRadius: 10, border: "none", cursor: "pointer",
                 background: palette.accent, color: palette.accentText, fontFamily: FONT.display }}>
          Try again
        </button>
      </div>
    );
  }

  if (!trip) {
    return (
      <div style={{ display: "grid", gap: SP.md, maxWidth: 640, margin: "0 auto" }}>
        <ActivityCardSkeleton /><ActivityCardSkeleton /><ActivityCardSkeleton />
      </div>
    );
  }

  return (
    <div className="tp-dash" style={{ display: "grid", gridTemplateColumns: "1fr min(320px, 34%)", gap: SP.lg, alignItems: "start" }}>
      {/* MAIN column */}
      <div>
        <div className="tp-noprint" style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: SP.md, marginBottom: SP.md }}>
          <h1 style={{ ...TYPE.h1, color: palette.text, margin: 0 }}>{trip.destination}</h1>
          <button onClick={onReset} style={ghost(palette)}>{t("new_trip", lang)}</button>
          <button onClick={share} style={ghost(palette)}><Share2 size={15} strokeWidth={1.8} /> {shareMsg || t("share", lang)}</button>
          <button onClick={() => window.print()} style={ghost(palette)}><Printer size={15} strokeWidth={1.8} /> PDF</button>
          <div style={{ marginLeft: "auto", display: "flex", background: palette.surfaceAlt, borderRadius: 999, padding: 3 }}>
            {(["list", "map"] as const).map((v) => (
              <button key={v} onClick={() => setView(v)} aria-pressed={view === v}
                style={{ ...TYPE.small, fontWeight: 600, minHeight: 38, padding: "6px 16px", borderRadius: 999, cursor: "pointer", border: "none",
                         background: view === v ? palette.accent : "transparent",
                         color: view === v ? palette.accentText : palette.text }}>
                {v === "list" ? "List" : "Map"}
              </button>
            ))}
          </div>
        </div>

        {/* day selector */}
        <div style={{ display: "flex", gap: SP.xs, marginBottom: SP.md, overflowX: "auto" }}>
          {trip.days.map((d) => (
            <button key={d.day_index} onClick={() => setActiveDay(d.day_index)} aria-pressed={d.day_index === activeDay}
              style={{ ...TYPE.small, fontWeight: 600, minHeight: 44, padding: "8px 18px", borderRadius: 999, cursor: "pointer", whiteSpace: "nowrap",
                       border: `1px solid ${d.day_index === activeDay ? palette.accent : palette.border}`,
                       background: d.day_index === activeDay ? palette.accent : palette.surface,
                       color: d.day_index === activeDay ? palette.accentText : palette.text }}>
              {t("day", lang)} {d.day_index}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div key={`${activeDay}-${view}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            exit={{ opacity: 0 }} transition={{ duration: MOTION.base }}>
            {view === "list" && day && <SortableDayView day={day} onReorder={reorder} highlightIds={highlightIds} />}
            {view === "map" && day && <MapView day={day} hotel={hotel} amenities={amenities} route={dayRoute} />}
          </motion.div>
        </AnimatePresence>

        {/* inject controls (disruption demo) — same code path as real events */}
        {day && day.activities.length > 0 && (
          <div style={{ marginTop: SP.md, display: "flex", flexWrap: "wrap", gap: SP.xs, alignItems: "center" }}>
            <span style={{ ...TYPE.small, color: palette.textDim, display: "inline-flex", alignItems: "center", gap: 6 }}>
              <CloudRain size={14} strokeWidth={1.8} /> Simulate disruption:
            </span>
            {[...day.activities].sort((a, b) => a.seq - b.seq).slice(0, 3).map((a) => (
              <button key={a.place_id} onClick={() => inject(a.place_id, "weather")} disabled={busy}
                style={{ ...TYPE.small, minHeight: 36, padding: "6px 12px", borderRadius: 8, cursor: "pointer",
                         border: "none", textDecoration: "underline", textUnderlineOffset: 3,
                         background: "transparent", color: palette.text }}>
                {a.name.slice(0, 22)}
              </button>
            ))}
          </div>
        )}

        {/* suggestions — satellite cards, smaller and quieter than activity cards */}
        {day && day.suggestions.filter((s) => s.rank === 1).length > 0 && (
          <div style={{ marginTop: SP.lg, display: "grid", gap: SP.sm, maxWidth: 520 }}>
            <h3 style={{ ...TYPE.small, fontWeight: 600, color: palette.textDim, margin: 0 }}>{t("suggestions", lang)}</h3>
            {day.suggestions.filter((s) => s.rank === 1).map((s) => (
              <SuggestionCard key={`${s.type}${s.place_id}`} type={s.type} name={s.place_name}
                timeWindow={s.time_window} website={s.website} />
            ))}
          </div>
        )}
      </div>

      {/* STICKY budget rail */}
      <div style={{ position: "sticky", top: SP.md, display: "grid", gap: SP.md }}>
        {budget && (
          <div style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: RADIUS, padding: SP.md, boxShadow: palette.shadow }}>
            <div style={{ ...TYPE.small, fontWeight: 600, color: palette.textDim }}>{t("budget_label", lang)}</div>
            <div style={{ ...TYPE.h1, color: budget.over_budget ? palette.beacon : palette.text, marginTop: 4,
                          fontVariantNumeric: "tabular-nums" }}>
              {sym}{budget.total.toLocaleString("en-IN")}
            </div>
            <div style={{ ...TYPE.small, color: palette.textDim }}>
              of {sym}{budget.budget_total.toLocaleString("en-IN")}
              {budget.over_budget ? <span style={{ color: palette.beacon, fontWeight: 600 }}> — over budget</span> : null}
            </div>
            <div style={{ height: 4, background: palette.surfaceAlt, borderRadius: 999, marginTop: SP.sm, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${Math.min(100, (budget.total / (budget.budget_total || 1)) * 100)}%`,
                            background: budget.over_budget ? palette.beacon : palette.accent }} />
            </div>
            <div style={{ marginTop: SP.sm, display: "grid", gap: 2 }}>
              {budget.per_day.map((p) => (
                <div key={p.day_index} style={{ display: "flex", justifyContent: "space-between", ...TYPE.small, color: palette.textDim,
                                                fontVariantNumeric: "tabular-nums" }}>
                  <span>{t("day", lang)} {p.day_index}</span><span>{sym}{p.cost.toLocaleString("en-IN")}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <AnimatePresence>
          {change && change.status === "pending" && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <DiffView change={change} onConfirm={confirm} onReject={reject} busy={busy} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <ChatPanel trip={trip} onApplied={applyChange}
        onTripReplaced={() => { setActiveDay(1); setDayRoute(null); refresh(); }} />
    </div>
  );
}

/** Secondary/tertiary action: plain text, no border, no fill, quiet icon. */
const ghost = (palette: { text: string; textDim: string }): React.CSSProperties => ({
  ...TYPE.small, fontWeight: 600, minHeight: 44, padding: "8px 10px", borderRadius: 8, cursor: "pointer",
  background: "transparent", color: palette.textDim, border: "none",
  display: "inline-flex", alignItems: "center", gap: 6,
});
