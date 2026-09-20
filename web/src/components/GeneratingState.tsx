import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useUI } from "../ui-context";
import { SP, TYPE, HARBOR } from "../theme";
import { t } from "../i18n";

/**
 * The one orchestrated motion moment: when a plan is generated, the route line
 * draws itself in (a pen tracing a path) while the status copy rotates. With
 * prefers-reduced-motion, the draw degrades to a simple fade.
 */
export function GeneratingState() {
  const { palette, lang } = useUI();
  const reduced = useReducedMotion();
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
      <motion.svg width="440" height="180" viewBox="0 0 440 180" fill="none"
        initial={reduced ? { opacity: 0 } : undefined} animate={reduced ? { opacity: 1 } : undefined}>
        <motion.path d={d} stroke={palette.border} strokeWidth={3} strokeDasharray="2 8" strokeLinecap="round" />
        <motion.path d={d} stroke={HARBOR} strokeWidth={4} strokeLinecap="round"
          initial={{ pathLength: reduced ? 1 : 0 }} animate={{ pathLength: 1 }}
          transition={reduced ? { duration: 0.3 } : { duration: 2.2, ease: "easeInOut", repeat: Infinity }} />
        {!reduced && (
          <motion.circle r={7} fill={HARBOR}
            animate={{ offsetDistance: ["0%", "100%"] }}
            style={{ offsetPath: `path("${d}")` } as React.CSSProperties}
            transition={{ duration: 2.2, ease: "easeInOut", repeat: Infinity }} />
        )}
      </motion.svg>

      <motion.p key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        style={{ ...TYPE.h3, color: palette.text, margin: 0 }}>
        {lines[i]}
      </motion.p>
      <div aria-hidden style={{ display: "flex", gap: 6 }}>
        {lines.map((_, k) => (
          <span key={k} style={{ width: 7, height: 7, borderRadius: "50%",
                                  background: k === i ? HARBOR : palette.border, transition: "background .3s" }} />
        ))}
      </div>
    </div>
  );
}
