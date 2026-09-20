import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api";
import { SP, TYPE, RADIUS, MOTION, tagColor, FONT } from "../theme";
import { useUI } from "../ui-context";
import { stepSwap } from "../motion";
import { t } from "../i18n";
import { GeneratingState } from "./GeneratingState";

const INTERESTS = ["culture", "history", "outdoor", "food", "shopping", "nightlife"];
const STEPS = ["destination", "dates", "starttime", "budget", "interests", "pace"] as const;
type Step = (typeof STEPS)[number];

/**
 * Screen 2 — conversational trip intake (one question at a time).
 * Sequential content, but per the guide NO decorative connecting line here —
 * the spine is earned only by genuinely sequential itinerary content.
 * Labels are Instrument Sans sentence case; helper prose is Newsreader.
 */
export function Intake({ onCreated }: { onCreated: (tripId: number) => void }) {
  const { palette, lang, setCurrency } = useUI();
  const [step, setStep] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [err, setErr] = useState("");

  const [destination, setDestination] = useState("Delhi");
  const [start, setStart] = useState("2026-09-25");
  const [end, setEnd] = useState("2026-09-27");
  const [startTime, setStartTime] = useState("09:00");
  const [budget, setBudget] = useState(6000);
  const [interests, setInterests] = useState<string[]>(["history", "culture", "outdoor"]);
  const [pace, setPace] = useState("balanced");

  // destination typeahead
  const [sug, setSug] = useState<{ id: number; name: string }[]>([]);
  useEffect(() => {
    if (!destination.trim()) { setSug([]); return; }
    const id = setTimeout(() => {
      api.placesSearch(destination).then(setSug).catch(() => setSug([]));
    }, 200);
    return () => clearTimeout(id);
  }, [destination]);

  const current: Step = STEPS[step];
  const canNext = useMemo(() => {
    if (current === "destination") return destination.trim().length > 1;
    if (current === "dates") return !!start && !!end && start <= end;
    if (current === "interests") return interests.length > 0;
    return true;
  }, [current, destination, start, end, interests]);

  const toggle = (tag: string) =>
    setInterests((cur) => (cur.includes(tag) ? cur.filter((x) => x !== tag) : [...cur, tag]));

  const advance = async () => {
    if (step < STEPS.length - 1) { setStep(step + 1); return; }
    // last step -> generate
    setGenerating(true);
    setErr("");
    try {
      const trip = await api.createTrip({
        destination, start_date: start, end_date: end, budget_total: budget,
        currency: "INR", interests, start_time_day1: startTime, pace, group_size: 1,
      });
      setCurrency("INR");
      // let the branded state show at least a beat
      await new Promise((r) => setTimeout(r, 900));
      onCreated(trip.id);
    } catch (e) {
      setErr("Couldn't generate the itinerary — check the backend is running, then try again.");
      setGenerating(false);
    }
  };

  if (generating) return <GeneratingState />;

  const pct = ((step + 1) / STEPS.length) * 100;

  return (
    <div style={{ maxWidth: 560, margin: "0 auto", minHeight: "60vh", display: "grid", alignContent: "center", gap: SP.lg }}>
      {/* progress */}
      <div style={{ height: 4, background: palette.surfaceAlt, borderRadius: 999, overflow: "hidden" }}>
        <motion.div animate={{ width: `${pct}%` }} transition={{ duration: MOTION.base, ease: MOTION.ease }}
          style={{ height: "100%", background: palette.accent }} />
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={current} variants={stepSwap} initial="hidden" animate="show" exit="exit"
          style={{ display: "grid", gap: SP.md }}>
          {current === "destination" && (
            <Q label={t("q_destination", lang)}>
              <input autoFocus value={destination} onChange={(e) => setDestination(e.target.value)}
                placeholder="Delhi" style={inp(palette)} />
              {sug.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: SP.xs }}>
                  {sug.slice(0, 5).map((s) => (
                    <button key={s.id} onClick={() => { setDestination(s.name); setSug([]); }}
                      style={{ ...TYPE.small, minHeight: 44, padding: "8px 14px", borderRadius: 999, cursor: "pointer",
                               border: `1px solid ${palette.border}`, background: palette.surface, color: palette.text }}>
                      {s.name}
                    </button>
                  ))}
                </div>
              )}
            </Q>
          )}

          {current === "dates" && (
            <Q label={t("q_dates", lang)}>
              <div style={{ display: "flex", gap: SP.sm }}>
                <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={inp(palette)} />
                <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={inp(palette)} />
              </div>
            </Q>
          )}

          {current === "starttime" && (
            <Q label={t("q_starttime", lang)} hint={t("q_starttime_hint", lang)}>
              <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} style={inp(palette)} />
            </Q>
          )}

          {current === "budget" && (
            <Q label={t("q_budget", lang)}>
              <div style={{ ...TYPE.h2, color: palette.text, fontVariantNumeric: "tabular-nums" }}>
                ₹{budget.toLocaleString("en-IN")}
              </div>
              <input type="range" min={1000} max={30000} step={500} value={budget}
                onChange={(e) => setBudget(Number(e.target.value))} style={{ width: "100%", accentColor: palette.accent }} />
            </Q>
          )}

          {current === "interests" && (
            <Q label={t("q_interests", lang)}>
              <div style={{ display: "flex", flexWrap: "wrap", gap: SP.sm }}>
                {INTERESTS.map((tag) => {
                  const on = interests.includes(tag);
                  return (
                    <motion.button key={tag} onClick={() => toggle(tag)} whileTap={{ scale: 0.97 }}
                      aria-pressed={on}
                      style={{ ...TYPE.body, fontFamily: FONT.display, fontSize: 15, minHeight: 44, padding: "10px 18px",
                               borderRadius: 999, cursor: "pointer",
                               border: `1.5px solid ${on ? palette.accent : tagColor(tag)}`,
                               background: on ? palette.accent : "transparent",
                               color: on ? palette.accentText : palette.text }}>
                      {tag}
                    </motion.button>
                  );
                })}
              </div>
            </Q>
          )}

          {current === "pace" && (
            <Q label={t("q_pace", lang)}>
              <div style={{ display: "flex", gap: SP.sm }}>
                {(["relaxed", "balanced", "packed"] as const).map((p) => (
                  <button key={p} onClick={() => setPace(p)} aria-pressed={pace === p}
                    style={{ ...TYPE.body, fontFamily: FONT.display, fontSize: 15, minHeight: 44, flex: 1, padding: "12px",
                             borderRadius: RADIUS, cursor: "pointer",
                             border: `1.5px solid ${pace === p ? palette.accent : palette.border}`,
                             background: pace === p ? palette.accent : palette.surface,
                             color: pace === p ? palette.accentText : palette.text }}>
                    {t(p, lang)}
                  </button>
                ))}
              </div>
            </Q>
          )}
        </motion.div>
      </AnimatePresence>

      {err && <p style={{ ...TYPE.small, color: "#B42318" }}>{err}</p>}

      <div style={{ display: "flex", gap: SP.sm, justifyContent: "space-between" }}>
        <button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}
          style={{ ...TYPE.body, fontFamily: FONT.display, fontSize: 15, fontWeight: 500, minHeight: 44,
                   padding: "10px 20px", borderRadius: RADIUS, cursor: "pointer",
                   border: "none", background: "transparent", color: palette.text,
                   opacity: step === 0 ? 0.4 : 1 }}>
          {t("back", lang)}
        </button>
        <button onClick={advance} disabled={!canNext}
          style={{ ...TYPE.h3, minHeight: 44, padding: "10px 28px", borderRadius: RADIUS, border: "none",
                   cursor: canNext ? "pointer" : "not-allowed", background: palette.accent, color: palette.accentText,
                   opacity: canNext ? 1 : 0.5 }}>
          {step === STEPS.length - 1 ? t("generate", lang) : t("next", lang)}
        </button>
      </div>
    </div>
  );
}

function Q({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  const { palette } = useUI();
  return (
    <div style={{ display: "grid", gap: SP.sm }}>
      <h1 style={{ ...TYPE.h1, color: palette.text, margin: 0 }}>{label}</h1>
      {hint && <p style={{ ...TYPE.narrative, fontSize: 15, color: palette.textDim, margin: 0 }}>{hint}</p>}
      {children}
    </div>
  );
}

const inp = (palette: { surface: string; surfaceAlt: string; text: string; border: string }): React.CSSProperties => ({
  ...TYPE.body, fontSize: 16, minHeight: 44, flex: 1, padding: "10px 14px", borderRadius: 10,
  background: palette.surface, color: palette.text, border: `1px solid ${palette.border}`,
});
