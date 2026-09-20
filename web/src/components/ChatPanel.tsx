import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MessageCircle, X } from "lucide-react";
import { api, type Change, type Trip } from "../api";
import { SP, TYPE, MOTION, INK, FONT } from "../theme";
import { useUI } from "../ui-context";
import { t } from "../i18n";
import { DiffView } from "./DiffView";

type Msg =
  | { role: "user"; text: string }
  | { role: "bot"; text: string }
  | { role: "diff"; change: Change };

/**
 * Screen 4 — floating chat panel. Always dark (Ink) regardless of app mode,
 * per the guide. Assistant messages are Newsreader italic — a distinct voice;
 * user messages are Instrument Sans. Expands/collapses in ~200ms. The typing
 * indicator is three dots with one slow easing pulse, not a bounce.
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
      push({ role: "bot", text: `That request didn't go through — try again in a moment.` });
    } finally {
      setBusy(false);
    }
  };

  const confirmDiff = async (idx: number, change: Change) => {
    setBusy(true);
    try {
      await onApplied(change);
      setMsgs((cur) => cur.map((m, i) => (i === idx ? { role: "bot", text: "Done — your itinerary is updated." } : m)));
    } finally { setBusy(false); }
  };
  const rejectDiff = async (idx: number, change: Change) => {
    setBusy(true);
    try {
      await api.reject(trip.id, change.id);
      setMsgs((cur) => cur.map((m, i) => (i === idx ? { role: "bot", text: "Nothing changed — the plan stands as it was." } : m)));
    } finally { setBusy(false); }
  };

  // Chat surfaces are always Ink, independent of the app mode.
  const ink = {
    surface: "#FFFFFF14",
    border: "#FFFFFF24",
    text: "#F1F3F0",
    dim: "#9CA5B4",
  };

  return (
    <>
      {/* dim veil behind the open panel */}
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
            style={{ position: "fixed", inset: 0, background: "rgba(16,21,31,0.45)", zIndex: 900 }} />
        )}
      </AnimatePresence>

      {/* floating button */}
      <motion.button onClick={() => setOpen((v) => !v)} aria-label={open ? "Close assistant" : "Open assistant"}
        whileTap={{ scale: 0.96 }}
        style={{ position: "fixed", bottom: 24, right: 24, zIndex: 1001, width: 56, height: 56, borderRadius: "50%",
                 border: "none", cursor: "pointer", background: palette.accent, color: palette.accentText,
                 display: "grid", placeItems: "center", boxShadow: palette.shadow }}>
        {open ? <X size={24} strokeWidth={1.8} /> : <MessageCircle size={24} strokeWidth={1.8} />}
      </motion.button>

      {/* panel */}
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, y: 24, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.98 }} transition={{ duration: MOTION.base, ease: MOTION.ease }}
            style={{ position: "fixed", bottom: 96, right: 24, zIndex: 1002, width: "min(420px, calc(100vw - 32px))",
                     height: "min(560px, calc(100vh - 140px))", display: "flex", flexDirection: "column",
                     background: INK, border: `1px solid ${ink.border}`, borderRadius: 16,
                     overflow: "hidden", boxShadow: palette.shadow }}>
            <div style={{ padding: SP.md, borderBottom: `1px solid ${ink.border}`, ...TYPE.h3, color: ink.text }}>
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
                  <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    style={{ justifySelf: mine ? "end" : "start", maxWidth: "85%",
                             ...(mine ? { ...TYPE.body, fontFamily: FONT.display, fontSize: 15 } : TYPE.narrative),
                             padding: "8px 12px", borderRadius: 12,
                             background: mine ? ink.surface : "transparent",
                             border: mine ? "none" : `1px solid transparent`,
                             color: mine ? ink.text : ink.dim }}>
                    {m.text}
                  </motion.div>
                );
              })}
              {busy && (
                <div aria-label={t("thinking", lang)}
                  style={{ justifySelf: "start", display: "flex", gap: 5, padding: "10px 4px" }}>
                  {[0, 1, 2].map((k) => (
                    <motion.span key={k} animate={{ opacity: [0.25, 1, 0.25] }}
                      transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
                      style={{ width: 6, height: 6, borderRadius: "50%", background: ink.dim }} />
                  ))}
                </div>
              )}
            </div>

            <div style={{ padding: SP.sm, borderTop: `1px solid ${ink.border}`, display: "flex", gap: SP.xs }}>
              <input value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder={t("chat_placeholder", lang)}
                style={{ ...TYPE.body, fontSize: 15, flex: 1, minHeight: 44, padding: "8px 12px", borderRadius: 10,
                         background: ink.surface, color: ink.text, border: `1px solid ${ink.border}` }} />
              <button onClick={send} disabled={busy}
                style={{ ...TYPE.body, fontFamily: FONT.display, fontSize: 15, fontWeight: 500, minHeight: 44,
                         padding: "8px 16px", borderRadius: 10, border: "none",
                         cursor: "pointer", background: palette.accent, color: palette.accentText }}>
                {t("ask", lang)}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
