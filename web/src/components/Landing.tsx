import { motion } from "framer-motion";
import { useUI } from "../ui-context";
import { SP, TYPE, RADIUS, MOTION, FONT } from "../theme";
import { fadeIn, stagger } from "../motion";
import { t } from "../i18n";

/**
 * Screen 1 — Landing. Left-aligned hero over a real destination photo with a
 * minimal ink overlay (guide: overlay kept minimal, never a gradient wash).
 * One primary CTA, label only — no arrow appended.
 */
export function Landing({ onStart }: { onStart: () => void }) {
  const { palette, lang, mode } = useUI();

  return (
    <section
      style={{
        position: "relative",
        minHeight: "78vh",
        borderRadius: 28,
        overflow: "hidden",
        display: "flex",
        alignItems: "flex-end",
        padding: SP.xxl,
        border: `1px solid ${palette.border}`,
        background: mode === "dark" ? palette.bg : "#DDE4DE",
      }}
    >
      {/* Real destination photo, treated as a document. Object-position keeps
          the city skyline visible behind the copy. */}
      <img
        src="https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=2000&q=70"
        alt="Paris rooftops at dusk"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }}
      />
      {/* minimal ink overlay for text contrast — no gradient wash */}
      <div aria-hidden style={{ position: "absolute", inset: 0, background: "rgba(16,21,31,0.52)" }} />

      <motion.div variants={stagger} initial="hidden" animate="show"
        style={{ position: "relative", maxWidth: 680, display: "grid", gap: SP.md, justifyItems: "start" }}>
        <motion.span variants={fadeIn}
          style={{ ...TYPE.small, fontWeight: 600, color: "#F1F3F0", opacity: 0.9 }}>
          TravelPilot
        </motion.span>
        <motion.h1 variants={fadeIn} style={{ ...TYPE.display, color: "#F1F3F0", margin: 0 }}>
          {t("app_title", lang)}
        </motion.h1>
        <motion.p variants={fadeIn} style={{ ...TYPE.narrative, color: "#F1F3F0", opacity: 0.95,
                   maxWidth: 520, margin: 0 }}>
          {t("app_subtitle", lang)}
        </motion.p>
        <motion.button variants={fadeIn} onClick={onStart}
          whileTap={{ scale: 0.98 }}
          transition={{ duration: MOTION.fast }}
          style={{ ...TYPE.h3, marginTop: SP.sm, padding: "16px 36px", minHeight: 48, borderRadius: RADIUS,
                   border: "none", cursor: "pointer", background: "#1F6F78", color: "#F1F3F0",
                   fontFamily: FONT.display }}>
          {t("start_planning", lang)}
        </motion.button>
      </motion.div>
    </section>
  );
}
