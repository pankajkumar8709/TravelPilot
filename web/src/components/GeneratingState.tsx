import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useUI } from "../ui-context";
import { SP, TYPE, ACCENT } from "../theme";
import { t } from "../i18n";

/**
 * Branded generation state — an animated route being "drawn" plus rotating
 * status lines. Intentional, not a generic spinner.
 */
export function GeneratingState() {
  const { palette, lang } = useUI();
  const lines = [t("gen_1", lang), t("gen_2", lang), t("gen_3", lang), t("gen_4", lang)];
  const [i, setI] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setI((v) => (v + 1) % lines.length), 1400);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  // a wandering path the "traveler" dot follows
  const d = "M20,120 C80,20 160,200 240,90 S360,40 420,120";
  return (
    <div style={{ display: "grid", placeItems: "center", gap: SP.lg, padding: SP.xl, minHeight: "50vh" }}>
      <svg width="440" height="180" viewBox="0 0 440 180" fill="none">
        <motion.path d={d} stroke={palette.border} strokeWidth={3} strokeDasharray="2 8" strokeLinecap="round" />
        <motion.path d={d} stroke={ACCENT} strokeWidth={4} strokeLinecap="round"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
          transition={{ duration: 2.2, ease: "easeInOut", repeat: Infinity }} />
        <motion.circle r={7} fill={ACCENT}
          animate={{
            offsetDistance: ["0%", "100%"],
          }}
          style={{ offsetPath: `path("${d}")` } as React.CSSProperties}
          transition={{ duration: 2.2, ease: "easeInOut", repeat: Infinity }} />
      </svg>

      <motion.p key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
        style={{ ...TYPE.h3, fontWeight: 500, color: palette.text, margin: 0 }}>
        {lines[i]}
      </motion.p>
      <div style={{ display: "flex", gap: 6 }}>
        {lines.map((_, k) => (
          <span key={k} style={{ width: 8, height: 8, borderRadius: "50%",
                                  background: k === i ? ACCENT : palette.border, transition: "background .3s" }} />
        ))}
      </div>
    </div>
  );
}
