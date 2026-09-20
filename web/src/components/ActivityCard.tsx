import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Activity } from "../api";
import { SP, TYPE, RADIUS, RADIUS_SUGGESTION, MOTION, tagColor, STATE } from "../theme";
import { useUI } from "../ui-context";
import { currencySymbol, t } from "../i18n";

/**
 * Activity card: photo (landscape crop), Instrument Sans title, Newsreader
 * description line, interest-tag color as a 3px left border (never a full
 * background). Hover treatment is a border shift only — no lift, no shadow
 * growth. Clicking expands it in place.
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
  const stateAccent =
    variant === "added" ? STATE.added :
    variant === "removed" ? STATE.removed :
    variant === "modified" ? STATE.modified :
    tagColor(activity.interest_tag);
  // state color carries a text label too (accessibility floor)
  const stateLabel =
    variant === "added" ? t("added", lang) :
    variant === "removed" ? t("removed", lang) :
    variant === "modified" ? t("rescheduled", lang) :
    "";

  return (
    <motion.div
      layout
      animate={highlight ? { boxShadow: [`0 0 0px ${stateAccent}00`, `0 0 16px ${stateAccent}88`, `0 0 0px ${stateAccent}00`] } : {}}
      transition={{ duration: 0.6 }}
      onClick={() => setOpen((v) => !v)}
      style={{
        background: palette.surface,
        border: `1px solid ${palette.border}`,
        borderLeft: `3px solid ${stateAccent}`,
        borderRadius: RADIUS,
        overflow: "hidden",
        cursor: "pointer",
        opacity: variant === "removed" ? 0.6 : 1,
        transition: "border-color 0.15s ease",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = palette.accent)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = palette.border)}
    >
      <div style={{ display: "flex", gap: SP.md, padding: SP.md, alignItems: "center" }}>
        {activity.image_url ? (
          <img src={activity.image_url} alt={activity.name} loading="lazy"
            style={{ width: 96, height: 72, objectFit: "cover", borderRadius: 8, flexShrink: 0 }} />
        ) : (
          <div style={{ width: 96, height: 72, borderRadius: 8, flexShrink: 0,
                        background: palette.surfaceAlt, display: "grid", placeItems: "center",
                        color: palette.textDim, ...TYPE.small }}>
            {activity.interest_tag}
          </div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ ...TYPE.small, color: palette.textDim, fontVariantNumeric: "tabular-nums",
                        display: "flex", gap: 8, alignItems: "center" }}>
            <span>{activity.start_time}–{activity.end_time}</span>
            {stateLabel && <span style={{ color: stateAccent, fontWeight: 600 }}>{stateLabel}</span>}
          </div>
          <div style={{ ...TYPE.cardTitle, color: palette.text, whiteSpace: "nowrap", overflow: "hidden",
                        textOverflow: "ellipsis",
                        textDecoration: variant === "removed" ? "line-through" : "none" }}>
            {activity.name}
          </div>
          <div style={{ ...TYPE.body, fontSize: 14, color: palette.textDim, display: "flex", gap: 10 }}>
            {activity.duration_minutes ? <span>{activity.duration_minutes} {t("min", lang)}</span> : null}
            <span>{activity.cost > 0 ? `${sym}${activity.cost.toFixed(0)}` : t("free", lang)}</span>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: MOTION.base, ease: MOTION.ease }}
            style={{ overflow: "hidden" }}>
            <div style={{ padding: `0 ${SP.md}px ${SP.md}px`, ...TYPE.body, color: palette.textDim, maxWidth: "72ch" }}>
              {activity.description
                || `A ${activity.interest_tag} stop on your route. Scheduled ${activity.start_time}–${activity.end_time}.`}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/**
 * Suggestion card (food/stay) — deliberately smaller and quieter than an
 * activity card: thinner border, radius 8 (vs 12), no photo by default,
 * Beacon-colored "view & book" link. The two card types never look alike.
 */
export function SuggestionCard({ type, name, timeWindow, website }: {
  type: "food" | "stay"; name: string; timeWindow: string; website: string;
}) {
  const { palette, lang } = useUI();
  const [expanded, setExpanded] = useState(false);
  const label = type === "food" ? t("sug_food", lang) : t("sug_stay", lang);
  return (
    <div style={{
      display: "flex", flexDirection: "column", gap: 4,
      background: palette.surface,
      border: `1px solid ${palette.border}`,
      borderRadius: RADIUS_SUGGESTION,
      padding: "10px 12px",
    }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
        <span style={{ ...TYPE.small, fontWeight: 600, color: palette.textDim }}>{label}</span>
        <span style={{ ...TYPE.cardTitle, fontSize: 15, color: palette.text }}>{name}</span>
        <span style={{ ...TYPE.small, color: palette.textDim }}>{timeWindow}</span>
      </div>
      {expanded && (
        <div style={{ ...TYPE.body, fontSize: 14, color: palette.textDim, maxWidth: "72ch" }}>
          {type === "food"
            ? "Chosen because it sits near your route at this time of day, and is likely open in this window."
            : "Chosen for tonight, balanced against tomorrow's first stop so the morning commute stays short."}
        </div>
      )}
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        {website && (
          <a href={website} target="_blank" rel="noreferrer"
            style={{ ...TYPE.small, fontWeight: 600, color: palette.beacon, textDecoration: "none" }}>
            {t("view_book", lang)}
          </a>
        )}
        <button onClick={() => setExpanded((v) => !v)}
          style={{ ...TYPE.small, border: "none", background: "transparent", cursor: "pointer",
                   color: palette.textDim, padding: 0 }}>
          {t("why_this", lang)}
        </button>
      </div>
    </div>
  );
}
