import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Dashboard } from "./components/Dashboard";
import { Intake } from "./components/Intake";
import { Landing } from "./components/Landing";
import { SP, TYPE, PALETTES, MOTION, type Mode } from "./theme";
import { LANGS, type Lang } from "./i18n";
import { UIContext } from "./ui-context";

type Screen = "landing" | "setup" | "dashboard";

export default function App() {
  const [screen, setScreen] = useState<Screen>("landing");
  const [tripId, setTripId] = useState<number | null>(null);
  const [lang, setLang] = useState<Lang>("en");
  const [currency, setCurrency] = useState("INR");
  const [mode, setMode] = useState<Mode>("dark");
  const palette = useMemo(() => PALETTES[mode], [mode]);

  return (
    <UIContext.Provider value={{ lang, setLang, currency, setCurrency, mode, setMode, palette }}>
      <div style={{ minHeight: "100vh", background: palette.bg, color: palette.text, padding: SP.xl,
                    transition: `background ${MOTION.base}s, color ${MOTION.base}s`,
                    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: SP.xs, marginBottom: SP.md }}>
            {LANGS.map((l) => (
              <button key={l.code} onClick={() => setLang(l.code)}
                style={{ ...TYPE.small, fontWeight: 600, padding: "4px 12px", borderRadius: 999, cursor: "pointer",
                         border: `1px solid ${palette.border}`,
                         background: lang === l.code ? palette.accent : palette.surface,
                         color: lang === l.code ? palette.accentText : palette.text }}>
                {l.label}
              </button>
            ))}
            <button onClick={() => setMode(mode === "dark" ? "light" : "dark")}
              title="Toggle theme"
              style={{ ...TYPE.small, marginLeft: SP.sm, padding: "4px 12px", borderRadius: 999, cursor: "pointer",
                       border: `1px solid ${palette.border}`, background: palette.surface, color: palette.text }}>
              {mode === "dark" ? "☀︎ Light" : "☾ Dark"}
            </button>
          </div>

          <AnimatePresence mode="wait">
            {screen === "landing" && (
              <motion.div key="landing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: MOTION.base }}>
                <Landing onStart={() => setScreen("setup")} />
              </motion.div>
            )}
            {screen === "setup" && (
              <motion.div key="setup" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }}
                transition={{ duration: MOTION.base }}>
                <Intake onCreated={(id) => { setTripId(id); setScreen("dashboard"); }} />
              </motion.div>
            )}
            {screen === "dashboard" && tripId !== null && (
              <motion.div key="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: MOTION.base }}>
                <Dashboard tripId={tripId} onReset={() => { setTripId(null); setScreen("landing"); }} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </UIContext.Provider>
  );
}
