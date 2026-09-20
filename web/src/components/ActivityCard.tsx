import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Activity } from "../api";
import { SP, TYPE, RADIUS, MOTION, tagColor, STATE } from "../theme";
import { useUI } from "../ui-context";
import { currencySymbol, t } from "../i18n";

/**
 * Premium activity card: real photo, name, time window, cost, interest-tag accent.
 * Clicking expands it smoothly in place (not a modal swap). Variant tints the
 * left accent for diff states (added/removed/modified).
 */
export function ActivityCard({
  activity,
  variant = "default",
  highlight = false,
}: {
  activity: Activity & { description?: string };
  variant?: "default" | "added" | "removed" | "modified";
  highlight?: boolean;
}) {
  const { palette, lang, currency } = useUI();
  const [open, setOpen] = useState(false);
  const sym = currencySymbol(currency);
  const accent =
    variant === "added" ? STATE.added :
    variant === "removed" ? STATE.removed :
    variant === "modified" ? STATE.modified :
    tagColor(activity.interest_tag);

  return (
    <motion.div
      layout
      onClick={() => setOpen((v) => !v)}
      animate={highlight ? { boxShadow: [`0 0 0px ${accent}00`, `0 0 24px ${accent}bb`, `0 0 0px ${accent}00`] } : {}}
      transition={{ duration: 1.2 }}
      whileHover={{ y: -2 }}
      style={{
        background: palette.surface,
        border: `1px solid ${palette.border}`,
        borderLeft: `4px solid ${accent}`,
        borderRadius: RADIUS,
        overflow: "hidden",
        cursor: "pointer",
        opacity: variant === "removed" ? 0.6 : 1,
        boxShadow: palette.shadow,
      }}
    >
      <div style={{ display: "flex", gap: SP.md, padding: SP.md, alignItems: "center" }}>
        {activity.image_url ? (
          <img src={activity.image_url} alt={activity.name} loading="lazy"
            style={{ width: 84, height: 64, objectFit: "cover", borderRadius: 12, flexShrink: 0 }} />
        ) : (
          <div style={{ width: 84, height: 64, borderRadius: 12, flexShrink: 0,
                        background: `linear-gradient(135deg, ${accent}, ${palette.surfaceAlt})` }} />
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ ...TYPE.small, color: palette.textDim, fontVariantNumeric: "tabular-nums" }}>
            {activity.start_time}–{activity.end_time}
          </div>
          <div style={{ ...TYPE.h3, color: palette.text, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                        textDecoration: variant === "removed" ? "line-through" : "none" }}>
            {activity.name}
          </div>
          <div style={{ ...TYPE.small, color: palette.textDim }}>
            {activity.duration_minutes ? `${activity.duration_minutes} ${t("min", lang)} · ` : ""}
            {activity.cost > 0 ? `${sym}${activity.cost.toFixed(0)}` : t("free", lang)}
          </div>
        </div>
        <span style={{ ...TYPE.small, color: "#0F1117", background: tagColor(activity.interest_tag),
                       padding: "2px 10px", borderRadius: 999, fontWeight: 700, flexShrink: 0 }}>
          {activity.interest_tag}
        </span>
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: MOTION.base, ease: MOTION.ease }}
            style={{ overflow: "hidden" }}>
            <div style={{ padding: `0 ${SP.md}px ${SP.md}px`, ...TYPE.body, color: palette.textDim }}>
              {activity.description
                || `A ${activity.interest_tag} stop on your route. Scheduled ${activity.start_time}–${activity.end_time}.`}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
