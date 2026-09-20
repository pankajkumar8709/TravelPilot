import { motion } from "framer-motion";
import type { Change } from "../api";
import { RADIUS, SP, TYPE, STATE, tagColor } from "../theme";
import { useUI } from "../ui-context";
import { currencySymbol, t } from "../i18n";

/**
 * Diff view + confirm-before-apply. Before/after of a pending change (disruption
 * OR chat add/move), plain-language reason, plan-stability score, confirm/reject.
 * Self-contained rows so it works with the diff's lightweight entries.
 */
export function DiffView({
  change,
  onConfirm,
  onReject,
  busy,
}: {
  change: Change;
  onConfirm: () => void;
  onReject: () => void;
  busy: boolean;
}) {
  const { lang, currency, palette } = useUI();
  const sym = currencySymbol(currency);
  const { diff, reason, trigger } = change;

  const row = (a: { place_id: number; name: string; start_time: string; end_time: string; cost: number; interest_tag: string },
               state: "added" | "removed") => (
    <div key={`${state}${a.place_id}`}
      style={{ display: "flex", alignItems: "center", gap: SP.sm, padding: SP.sm, borderRadius: 10,
               background: palette.surfaceAlt, borderLeft: `4px solid ${STATE[state]}`,
               opacity: state === "removed" ? 0.6 : 1 }}>
      <span style={{ ...TYPE.small, fontWeight: 700, color: STATE[state], textTransform: "uppercase", minWidth: 62 }}>
        {t(state, lang)}
      </span>
      <span style={{ flex: 1, ...TYPE.body, color: palette.text,
                     textDecoration: state === "removed" ? "line-through" : "none" }}>{a.name}</span>
      {a.start_time && <span style={{ ...TYPE.small, color: palette.textDim }}>{a.start_time}–{a.end_time}</span>}
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: tagColor(a.interest_tag) }} />
    </div>
  );

  return (
    <div style={{ background: palette.surface, border: `1px solid ${STATE.modified}`, borderRadius: RADIUS, padding: SP.md, boxShadow: palette.shadow }}>
      <div style={{ display: "flex", alignItems: "center", gap: SP.sm, marginBottom: SP.sm }}>
        <span style={{ ...TYPE.small, background: STATE.modified, color: "#0F1117", padding: "2px 10px", borderRadius: 999, fontWeight: 700 }}>
          {trigger.replace("_", " ").toUpperCase()}
        </span>
        <span style={{ ...TYPE.small, color: palette.textDim }}>{t("day", lang)} {diff.day_index}</span>
        <span style={{ marginLeft: "auto", ...TYPE.h3, color: palette.accent }}>
          {diff.stability}% {t("plan_stable", lang)}
        </span>
      </div>

      <p style={{ ...TYPE.body, color: palette.text, marginTop: 0 }}>{reason}</p>

      <div style={{ display: "grid", gap: SP.xs, marginTop: SP.sm }}>
        {diff.removed.map((a) => row(a, "removed"))}
        {diff.added.map((a) => row(a, "added"))}
        {diff.modified.map((m) => (
          <div key={`m${m.place_id}`} style={{ ...TYPE.small, color: palette.text, padding: SP.sm }}>
            <b>{m.name}</b>: <span style={{ color: palette.textDim }}>{m.from}</span> → <b>{m.to}</b>
          </div>
        ))}
        {sym && diff.added.some((a) => a.cost > 0) && (
          <div style={{ ...TYPE.small, color: palette.textDim, paddingTop: 2 }}>
            +{sym}{diff.added.reduce((s, a) => s + a.cost, 0).toLocaleString("en-IN")}
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: SP.sm, marginTop: SP.md }}>
        <motion.button whileTap={{ scale: 0.97 }} onClick={onConfirm} disabled={busy}
          style={{ ...TYPE.body, fontWeight: 600, flex: 1, padding: "10px", borderRadius: 10, cursor: "pointer",
                   background: STATE.added, color: "#0F1117", border: "none", opacity: busy ? 0.6 : 1 }}>
          {t("confirm_change", lang)}
        </motion.button>
        <button onClick={onReject} disabled={busy}
          style={{ ...TYPE.body, fontWeight: 600, flex: 1, padding: "10px", borderRadius: 10, cursor: "pointer",
                   background: "transparent", color: STATE.removed, border: `1px solid ${STATE.removed}`, opacity: busy ? 0.6 : 1 }}>
          {t("reject", lang)}
        </button>
      </div>
    </div>
  );
}
