import { useUI } from "../ui-context";

/** Shimmer skeleton block for loading states (not a blank screen). */
export function Skeleton({
  width = "100%",
  height = 16,
  radius = 8,
  style,
}: {
  width?: number | string;
  height?: number | string;
  radius?: number;
  style?: React.CSSProperties;
}) {
  const { palette } = useUI();
  return (
    <div
      style={{
        width,
        height,
        borderRadius: radius,
        background: `linear-gradient(90deg, ${palette.surfaceAlt} 25%, ${palette.border} 50%, ${palette.surfaceAlt} 75%)`,
        backgroundSize: "200% 100%",
        animation: "tp-shimmer 1.3s ease-in-out infinite",
        ...style,
      }}
    />
  );
}

/** A card-shaped skeleton matching the activity-card layout. */
export function ActivityCardSkeleton() {
  const { palette } = useUI();
  return (
    <div style={{ display: "flex", gap: 16, background: palette.surface, border: `1px solid ${palette.border}`,
                  borderRadius: 16, padding: 16 }}>
      <Skeleton width={96} height={72} radius={12} />
      <div style={{ flex: 1, display: "grid", gap: 8, alignContent: "center" }}>
        <Skeleton width="60%" height={16} />
        <Skeleton width="35%" height={12} />
      </div>
    </div>
  );
}
