import type { Change } from "../api";
import { RADIUS, SP, TYPE, STATE, tagColor, BEACON, FONT } from "../theme";
import { useUI } from "../ui-context";
import { currencySymbol, t } from "../i18n";

/**
 * Diff card — before/after of a pending change (disruption OR chat edit).
 * Changed rows carry a thin Beacon left border; the confirm button is Beacon
 * (the "forward" action); reject is plain text, deliberately not a competing
 * bright color. State words (added/removed/rescheduled) always accompany any
 * color signal.
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
      style={{ display: "flex", alignItems: "center", gap: SP.sm, padding: "8px 10px", borderRadius: 8,
               background: palette.surfaceAlt, borderLeft: `3px solid ${BEACON}`,
               opacity: state === "removed" ? 0.65 : 1 }}>
      <span style={{ ...TYPE.small, fontWeight: 600, color: STATE[state], minWidth: 74 }}>
        {t(state, lang)}
      </span>
      <span style={{ flex: 1, ...TYPE.body, fontSize: 15, color: palette.text,
                     textDecoration: state === "removed" ? "line-through" : "none" }}>{a.name}</span>
      {a.start_time && <span style={{ ...TYPE.small, color: palette.textDim, fontVariantNumeric: "tabular-nums" }}>{a.start_time}–{a.end_time}</span>}
      <span aria-hidden style={{ width: 8, height: 8, borderRadius: "50%", background: tagColor(a.interest_tag) }} />
    </div>
  );

  return (
    <div style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: RADIUS, padding: SP.md, boxShadow: palette.shadow }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: SP.sm, marginBottom: SP.sm }}>
        <span style={{ ...TYPE.small, fontWeight: 600, color: palette.textDim }}>
          {trigger.replace("_", " ")} — {t("day", lang)} {diff.day_index}
        </span>
        <span style={{ marginLeft: "auto", ...TYPE.h3, color: palette.accent, fontVariantNumeric: "tabular-nums" }}>
          {diff.stability}% {t("plan_stable", lang)}
        </span>
      </div>

      <p style={{ ...TYPE.narrative, color: palette.text, marginTop: 0, maxWidth: "72ch" }}>{reason}</p>

      <div style={{ display: "grid", gap: 6, marginTop: SP.sm }}>
        {diff.removed.map((a) => row(a, "removed"))}
        {diff.added.map((a) => row(a, "added"))}
        {diff.modified.map((m) => (
          <div key={`m${m.place_id}`}
            style={{ display: "flex", alignItems: "baseline", gap: 6, padding: "8px 10px", borderRadius: 8,
                     background: palette.surfaceAlt, borderLeft: `3px solid ${BEACON}` }}>
            <span style={{ ...TYPE.small, fontWeight: 600, color: STATE.modified, minWidth: 74 }}>{t("rescheduled", lang)}</span>
            <span style={{ ...TYPE.body, fontSize: 15, color: palette.text }}>{m.name}</span>
            <span style={{ ...TYPE.small, color: palette.textDim, fontVariantNumeric: "tabular-nums", marginLeft: "auto" }}>
              {m.from} → {m.to}
            </span>
          </div>
        ))}
        {sym && diff.added.some((a) => a.cost > 0) && (
          <div style={{ ...TYPE.small, color: palette.beacon, fontWeight: 600, paddingTop: 2 }}>
            +{sym}{diff.added.reduce((s, a) => s + a.cost, 0).toLocaleString("en-IN")}
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: SP.md, marginTop: SP.md, alignItems: "center" }}>
        <button onClick={onConfirm} disabled={busy}
          style={{ ...TYPE.h3, fontSize: 15, flex: 1, minHeight: 44, padding: "10px", borderRadius: 10, cursor: "pointer",
                   background: BEACON, color: "#10151F", border: "none", fontFamily: FONT.display,
                   opacity: busy ? 0.6 : 1 }}>
          {t("confirm_change", lang)}
        </button>
        <button onClick={onReject} disabled={busy}
          style={{ ...TYPE.body, fontFamily: FONT.display, fontSize: 15, fontWeight: 500, minHeight: 44,
                   padding: "10px 16px", borderRadius: 10, cursor: "pointer",
                   background: "transparent", color: palette.textDim, border: "none", opacity: busy ? 0.6 : 1 }}>
          {t("reject", lang)}
        </button>
      </div>
    </div>
  );
}
