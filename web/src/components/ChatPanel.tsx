import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, type Change, type Trip } from "../api";
import { SP, TYPE, MOTION } from "../theme";
import { useUI } from "../ui-context";
import { t } from "../i18n";
import { DiffView } from "./DiffView";

type Msg =
  | { role: "user"; text: string }
  | { role: "bot"; text: string }
  | { role: "diff"; change: Change };

/**
 * Screen 4 — floating animated chat panel.
 * Floating pulse button → expands over a dimmed itinerary (not replacing it).
 * Routes ADD/MOVE → diff card w/ confirm-in-chat; QUESTION → inline answer.
 * On confirm, calls onApplied so the itinerary refreshes + highlights.
 */
export function ChatPanel({
  trip,
  onApplied,
}: {
  trip: Trip;
  onApplied: (change: Change) => Promise<void>;
}) {
  const { palette, lang } = useUI();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([{ role: "bot", text: t("chat_greeting", lang) }]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 1e6, behavior: "smooth" });
  }, [msgs, busy]);

  const push = (m: Msg) => setMsgs((cur) => [...cur, m]);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    push({ role: "user", text });
    setBusy(true);
    try {
      const low = text.toLowerCase();
      // ADD: "add <place>"
      const addM = low.match(/\badd\s+(.+)/);
      // MOVE: "move <place> to day N"
      const moveM = low.match(/\bmove\s+(.+?)\s+to\s+day\s*(\d+)/);
      if (moveM) {
        const name = moveM[1];
        const toDay = parseInt(moveM[2], 10);
        const act = trip.days.flatMap((d) => d.activities).find((a) => a.name.toLowerCase().includes(name));
        if (!act) { push({ role: "bot", text: `I couldn't find "${name}" in your plan.` }); }
        else {
          const change = await api.chatMove({ trip_id: trip.id, place_id: act.place_id, to_day_index: toDay, lang });
          push({ role: "diff", change });
        }
      } else if (addM) {
        let query = addM[1];
        // extract an optional target day: "in day 3" / "on day 3" / "to day 3"
        const dayM = query.match(/\b(?:in|on|to)\s+day\s*(\d+)/);
        const dayIndex = dayM ? parseInt(dayM[1], 10) : null;
        // strip day phrases and plan/trip filler from the place name
        query = query
          .replace(/\b(?:in|on|to)\s+day\s*\d+/g, "")
          .replace(/\bto (my )?(plan|trip|itinerary)\b/g, "")
          .replace(/\s+/g, " ")
          .trim();
        if (!query) { push({ role: "bot", text: "Which place should I add?" }); }
        else {
          const change = await api.chatAdd({ trip_id: trip.id, place_query: query, day_index: dayIndex, lang });
          push({ role: "diff", change });
        }
      } else {
        const r = await api.nl({ trip_id: trip.id, question: text, lang });
        push({ role: "bot", text: r.answer });
      }
    } catch (e) {
      push({ role: "bot", text: `Sorry — ${String(e).replace("Error: ", "")}` });
    } finally {
      setBusy(false);
    }
  };

  const confirmDiff = async (idx: number, change: Change) => {
    setBusy(true);
    try {
      await onApplied(change);
      setMsgs((cur) => cur.map((m, i) => (i === idx ? { role: "bot", text: "✓ Done — your itinerary is updated." } : m)));
    } finally { setBusy(false); }
  };
  const rejectDiff = async (idx: number, change: Change) => {
    setBusy(true);
    try {
      await api.reject(trip.id, change.id);
      setMsgs((cur) => cur.map((m, i) => (i === idx ? { role: "bot", text: "No problem — nothing changed." } : m)));
    } finally { setBusy(false); }
  };

  return (
    <>
      {/* dim veil behind the open panel */}
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
            style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 900 }} />
        )}
      </AnimatePresence>

      {/* floating button */}
      <motion.button onClick={() => setOpen((v) => !v)}
        whileHover={{ scale: 1.06 }} whileTap={{ scale: 0.94 }}
        style={{ position: "fixed", bottom: 24, right: 24, zIndex: 1001, width: 60, height: 60, borderRadius: "50%",
                 border: "none", cursor: "pointer", background: palette.accent, color: palette.accentText,
                 fontSize: 26, boxShadow: palette.shadow,
                 animation: open ? "none" : "tp-pulse 2.4s ease-in-out infinite" }}>
        {open ? "✕" : "✦"}
      </motion.button>

      {/* panel */}
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, y: 30, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.98 }} transition={{ duration: MOTION.base, ease: MOTION.ease }}
            style={{ position: "fixed", bottom: 96, right: 24, zIndex: 1002, width: "min(420px, calc(100vw - 32px))",
                     height: "min(560px, calc(100vh - 140px))", display: "flex", flexDirection: "column",
                     background: palette.bgElev, border: `1px solid ${palette.border}`, borderRadius: 20,
                     overflow: "hidden", boxShadow: palette.shadow }}>
            <div style={{ padding: SP.md, borderBottom: `1px solid ${palette.border}`, ...TYPE.h3, color: palette.text }}>
              {t("chat_title", lang)}
            </div>

            <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: SP.md, display: "grid", gap: SP.sm, alignContent: "start" }}>
              {msgs.map((m, i) => {
                if (m.role === "diff") {
                  return (
                    <div key={i}>
                      <DiffView change={m.change} busy={busy}
                        onConfirm={() => confirmDiff(i, m.change)} onReject={() => rejectDiff(i, m.change)} />
                    </div>
                  );
                }
                const mine = m.role === "user";
                return (
                  <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                    style={{ justifySelf: mine ? "end" : "start", maxWidth: "85%",
                             ...TYPE.body, padding: "8px 12px", borderRadius: 14,
                             background: mine ? palette.accent : palette.surfaceAlt,
                             color: mine ? palette.accentText : palette.text }}>
                    {m.text}
                  </motion.div>
                );
              })}
              {busy && (
                <div style={{ justifySelf: "start", display: "flex", gap: 4, padding: "10px 12px" }}>
                  {[0, 1, 2].map((k) => (
                    <motion.span key={k} animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 0.9, repeat: Infinity, delay: k * 0.15 }}
                      style={{ width: 7, height: 7, borderRadius: "50%", background: palette.textDim }} />
                  ))}
                </div>
              )}
            </div>

            <div style={{ padding: SP.sm, borderTop: `1px solid ${palette.border}`, display: "flex", gap: SP.xs }}>
              <input value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder={t("chat_placeholder", lang)}
                style={{ ...TYPE.body, flex: 1, padding: "10px 12px", borderRadius: 12,
                         background: palette.surfaceAlt, color: palette.text, border: `1px solid ${palette.border}` }} />
              <button onClick={send} disabled={busy}
                style={{ ...TYPE.body, fontWeight: 600, padding: "10px 16px", borderRadius: 12, border: "none",
                         cursor: "pointer", background: palette.accent, color: palette.accentText }}>
                →
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
