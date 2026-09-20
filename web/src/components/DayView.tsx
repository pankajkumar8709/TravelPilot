import { motion } from "framer-motion";
import type { Activity, Day } from "../api";
import { SP, TYPE, tagColor, ACCENT } from "../theme";
import { useUI } from "../ui-context";
import { stagger, fadeIn } from "../motion";
import { ActivityCard } from "./ActivityCard";

/**
 * Connected-path day view: activities in visit order, each joined to the next by
 * an animated route line with a numbered, tag-colored node — the "journey" is
 * visible without opening the map.
 */
export function DayView({ day, highlightIds = [] }: { day: Day; highlightIds?: number[] }) {
  const { palette } = useUI();
  const acts = [...day.activities].sort((a, b) => a.seq - b.seq);

  if (!acts.length) {
    return <p style={{ ...TYPE.body, color: palette.textDim }}>No activities scheduled this day.</p>;
  }

  return (
    <motion.div variants={stagger} initial="hidden" animate="show"
      style={{ display: "grid", gridTemplateColumns: "36px 1fr", columnGap: SP.md }}>
      {acts.map((a: Activity, i) => (
        <motion.div key={a.place_id} variants={fadeIn} style={{ display: "contents" }}>
          {/* rail: numbered node + connecting line */}
          <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", flexShrink: 0, zIndex: 1,
                          display: "grid", placeItems: "center", ...TYPE.small, fontWeight: 800,
                          color: "#0F1117", background: tagColor(a.interest_tag),
                          border: `2px solid ${palette.bg}` }}>
              {i + 1}
            </div>
            {i < acts.length - 1 && (
              <motion.div initial={{ scaleY: 0 }} animate={{ scaleY: 1 }}
                transition={{ duration: 0.4, delay: 0.1 + i * 0.06 }}
                style={{ flex: 1, width: 3, transformOrigin: "top", marginTop: 2,
                         background: `linear-gradient(${tagColor(a.interest_tag)}, ${ACCENT})`, borderRadius: 2 }} />
            )}
          </div>
          {/* card */}
          <div style={{ paddingBottom: SP.md }}>
            <ActivityCard activity={a} highlight={highlightIds.includes(a.place_id)} />
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}
