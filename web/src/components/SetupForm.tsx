import { useEffect, useState } from "react";
import { api, type Place } from "../api";
import { COLORS, RADIUS, SP, tagColor, TYPE } from "../theme";
import { useUI } from "../ui-context";
import { t } from "../i18n";

const INTERESTS = ["culture", "history", "outdoor", "food", "shopping", "nightlife"];

/** Phase 1 screen 1: Setup form — destination, dates, budget, interests. */
export function SetupForm({ onCreated }: { onCreated: (tripId: number) => void }) {
  const { lang, setCurrency } = useUI();
  const [hotels, setHotels] = useState<Place[]>([]);
  const [start, setStart] = useState("2026-09-25");
  const [end, setEnd] = useState("2026-09-27");
  const [budget, setBudget] = useState(6000);
  const [interests, setInterests] = useState<string[]>(["history", "culture", "outdoor"]);
  const [hotelId, setHotelId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.places().then((ps) => {
      const hs = ps.filter((p) => p.category === "hotel");
      setHotels(hs);
      if (hs[0]) setHotelId(hs[0].id);
    }).catch((e) => setErr(String(e)));
  }, []);

  const toggle = (tag: string) =>
    setInterests((cur) => (cur.includes(tag) ? cur.filter((x) => x !== tag) : [...cur, tag]));

  const submit = async () => {
    setBusy(true);
    setErr("");
    try {
      const trip = await api.createTrip({
        destination: "Delhi", start_date: start, end_date: end,
        budget_total: budget, currency: "INR", interests, hotel_place_id: hotelId,
      });
      setCurrency("INR");
      onCreated(trip.id);
    } catch (e) {
      setErr(String(e));
      setBusy(false);
    }
  };

  return (
    <div style={{ maxWidth: 520, margin: "0 auto" }}>

      <h1 style={{ ...TYPE.h1, color: COLORS.text }}>{t("app_title", lang)}</h1>
      <p style={{ ...TYPE.body, color: COLORS.textDim, marginTop: 0 }}>
        {t("app_subtitle", lang)}
      </p>

      <Field label={t("dates", lang)}>
        <div style={{ display: "flex", gap: SP.sm }}>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={inp} />
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={inp} />
        </div>
      </Field>

      <Field label={`${t("budget", lang)} (₹${budget})`}>
        <input type="range" min={1000} max={30000} step={500} value={budget}
          onChange={(e) => setBudget(Number(e.target.value))} style={{ width: "100%" }} />
      </Field>

      <Field label={t("interests", lang)}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: SP.sm }}>
          {INTERESTS.map((tag) => {
            const on = interests.includes(tag);
            return (
              <button key={tag} onClick={() => toggle(tag)}
                style={{ ...TYPE.small, fontWeight: 600, padding: "6px 14px", borderRadius: 999, cursor: "pointer",
                         border: `1px solid ${tagColor(tag)}`,
                         background: on ? tagColor(tag) : "transparent",
                         color: on ? "#0F1117" : tagColor(tag) }}>
                {tag}
              </button>
            );
          })}
        </div>
      </Field>

      <Field label={t("hotel", lang)}>
        <select value={hotelId ?? ""} onChange={(e) => setHotelId(Number(e.target.value))} style={inp}>
          {hotels.map((h) => <option key={h.id} value={h.id}>{h.name} — ₹{h.cost}/night</option>)}
        </select>
      </Field>

      {err && <p style={{ ...TYPE.small, color: COLORS.removed }}>{err}</p>}

      <button onClick={submit} disabled={busy || interests.length === 0}
        style={{ ...TYPE.h3, width: "100%", padding: "12px", marginTop: SP.md, borderRadius: RADIUS,
                 border: "none", cursor: "pointer", background: COLORS.accent, color: "#0F1117",
                 opacity: busy || !interests.length ? 0.6 : 1 }}>
        {busy ? t("generating", lang) : t("generate", lang)}
      </button>
    </div>
  );
}

const inp: React.CSSProperties = {
  ...TYPE.body, flex: 1, padding: "8px 10px", borderRadius: 8,
  background: COLORS.surfaceAlt, color: COLORS.text, border: `1px solid ${COLORS.border}`,
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: SP.md }}>
      <label style={{ ...TYPE.small, color: COLORS.textDim, display: "block", marginBottom: SP.xs }}>{label}</label>
      {children}
    </div>
  );
}
