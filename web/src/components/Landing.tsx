import { motion } from "framer-motion";
import { useUI } from "../ui-context";
import { SP, TYPE, RADIUS, MOTION } from "../theme";
import { fadeIn, stagger } from "../motion";
import { t } from "../i18n";

/**
 * Screen 1 — Landing / Plan Your Trip.
 * Full-viewport hero with a slowly-panning animated gradient (not a static image),
 * a headline + subheadline, and ONE primary CTA into the intake flow.
 */
export function Landing({ onStart }: { onStart: () => void }) {
  const { palette, lang, mode } = useUI();

  // Warm travel-toned gradient; darker in dark mode for text contrast.
  const g =
    mode === "dark"
      ? "linear-gradient(120deg, #0F1117 0%, #1b2340 30%, #3a2b52 55%, #4a2f3d 80%, #0F1117 100%)"
      : "linear-gradient(120deg, #dff5f2 0%, #cfe0ff 30%, #e7d8ff 55%, #ffe2d6 80%, #dff5f2 100%)";

  return (
    <section
      style={{
        position: "relative",
        minHeight: "78vh",
        borderRadius: 28,
        overflow: "hidden",
        display: "grid",
        placeItems: "center",
        textAlign: "center",
        padding: SP.xl,
        border: `1px solid ${palette.border}`,
      }}
    >
      {/* animated panning gradient layer */}
      <motion.div
        aria-hidden
        style={{ position: "absolute", inset: -80, background: g, backgroundSize: "200% 200%", filter: "saturate(1.1)" }}
        animate={{ backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"] }}
        transition={{ duration: 22, ease: "easeInOut", repeat: Infinity }}
      />
      {/* soft darkening veil for contrast */}
      <div style={{ position: "absolute", inset: 0,
                    background: mode === "dark" ? "rgba(10,12,18,0.35)" : "rgba(255,255,255,0.18)" }} />
      {/* drifting glow orbs */}
      <motion.div aria-hidden
        style={{ position: "absolute", width: 340, height: 340, borderRadius: "50%",
                 background: "radial-gradient(circle, rgba(45,212,191,0.35), transparent 70%)", top: "8%", left: "10%" }}
        animate={{ x: [0, 40, 0], y: [0, 24, 0] }} transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }} />
      <motion.div aria-hidden
        style={{ position: "absolute", width: 300, height: 300, borderRadius: "50%",
                 background: "radial-gradient(circle, rgba(142,124,255,0.30), transparent 70%)", bottom: "6%", right: "12%" }}
        animate={{ x: [0, -36, 0], y: [0, -20, 0] }} transition={{ duration: 17, repeat: Infinity, ease: "easeInOut" }} />

      <motion.div variants={stagger} initial="hidden" animate="show"
        style={{ position: "relative", maxWidth: 720, display: "grid", gap: SP.md, justifyItems: "center" }}>
        <motion.span variants={fadeIn}
          style={{ ...TYPE.small, letterSpacing: "0.18em", textTransform: "uppercase",
                   color: palette.text, opacity: 0.85, fontWeight: 700 }}>
          TravelPilot
        </motion.span>
        <motion.h1 variants={fadeIn} style={{ ...TYPE.display, color: palette.text, margin: 0,
                   textShadow: mode === "dark" ? "0 2px 30px rgba(0,0,0,0.5)" : "none" }}>
          {t("app_title", lang)}
        </motion.h1>
        <motion.p variants={fadeIn} style={{ ...TYPE.h3, fontWeight: 400, color: palette.text, opacity: 0.9,
                   maxWidth: 520, margin: 0 }}>
          {t("app_subtitle", lang)}
        </motion.p>
        <motion.button variants={fadeIn} onClick={onStart}
          whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}
          transition={{ duration: MOTION.fast }}
          style={{ ...TYPE.h3, marginTop: SP.sm, padding: "14px 32px", borderRadius: RADIUS,
                   border: "none", cursor: "pointer", background: palette.accent, color: palette.accentText,
                   boxShadow: palette.shadow }}>
          {t("start_planning", lang)} →
        </motion.button>
      </motion.div>
    </section>
  );
}
