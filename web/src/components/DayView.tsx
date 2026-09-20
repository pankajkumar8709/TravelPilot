import { motion } from "framer-motion";
import type { Activity, Day } from "../api";
import { SP, TYPE, tagColor, HARBOR, FONT } from "../theme";
import { useUI } from "../ui-context";
import { stagger, fadeIn } from "../motion";
import { t, type Lang } from "../i18n";
import { ActivityCard } from "./ActivityCard";

/**
 * Connected-path day view — the journey spine. A single Harbor route line runs
 * down the left edge; numbered, tag-colored nodes sit on it; travel time labels
 * sit directly on the line between stops. Cards attach to the spine (single
 * column — the guide's mobile rule, kept here for clarity at all widths).
 */
export function DayView({ day, highlightIds = [] }: { day: Day; highlightIds?: number[] }) {
  const { palette, lang } = useUI();
  const acts = [...day.activities].sort((a, b) => a.seq - b.seq);

  if (!acts.length) {
    return (
      <p style={{ ...TYPE.narrative, color: palette.textDim }}>
        No activities scheduled this day — ask the assistant to add something.
      </p>
    );
  }

  return (
    <motion.div variants={stagger} initial="hidden" animate="show"
      style={{ display: "grid", gridTemplateColumns: "36px 1fr", columnGap: SP.md }}>
      {acts.map((a: Activity, i) => (
        <motion.div key={a.place_id} variants={fadeIn} style={{ display: "contents" }}>
          {/* rail: numbered node + connecting line */}
          <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", flexShrink: 0, zIndex: 1,
                          display: "grid", placeItems: "center", ...TYPE.small, fontWeight: 600,
                          color: "#F1F3F0", background: tagColor(a.interest_tag),
                          border: `2px solid ${palette.bg}` }}>
              {i + 1}
            </div>
            {i < acts.length - 1 && (
              <motion.div initial={{ scaleY: 0 }} animate={{ scaleY: 1 }}
                transition={{ duration: 0.4, delay: 0.1 + i * 0.06 }}
                style={{ flex: 1, width: 2, transformOrigin: "top", marginTop: 2,
                         background: HARBOR, borderRadius: 2 }} />
            )}
          </div>
          {/* card */}
          <div style={{ paddingBottom: SP.md }}>
            <ActivityCard activity={a} highlight={highlightIds.includes(a.place_id)} />
            {/* travel time to the NEXT stop, sitting directly on the spine */}
            {i < acts.length - 1 && (
              <div style={{ display: "flex", alignItems: "center", gap: 6, minHeight: 22,
                            marginTop: -6, marginBottom: 6, paddingLeft: 2 }}>
                <span style={{ width: 5, height: 5, borderRadius: "50%", background: HARBOR, flexShrink: 0 }} />
                <span style={{ ...TYPE.small, color: HARBOR, fontWeight: 500, fontFamily: FONT.display }}>
                  {travelLabel(acts[i], acts[i + 1], lang)}
                </span>
              </div>
            )}
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}

/** Gap between one stop's end and the next stop's start IS the travel buffer. */
function travelLabel(a: Activity, b: Activity, lang: Lang): string {
  const gap = Math.max(0, toMin(b.start_time) - toMin(a.end_time));
  if (gap <= 0) return t("to_next", lang);
  if (gap < 60) return `${Math.round(gap)} ${t("min", lang)} ${t("to_next", lang)}`;
  const h = Math.floor(gap / 60), m = Math.round(gap % 60);
  const dur = m ? `${h} ${t("h_unit", lang)} ${m} ${t("min", lang)}` : `${h} ${t("h_unit", lang)}`;
  return `${dur} ${t("to_next", lang)}`;
}

function toMin(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return (h || 0) * 60 + (m || 0);
}
