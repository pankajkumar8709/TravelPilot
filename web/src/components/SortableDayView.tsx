import { DndContext, closestCenter, PointerSensor, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Activity, Day } from "../api";
import { SP, TYPE, tagColor, HARBOR } from "../theme";
import { useUI } from "../ui-context";
import { ActivityCard } from "./ActivityCard";

/**
 * Drag-to-reorder day view — same journey spine as DayView (Harbor line,
 * numbered tag-colored nodes, travel labels between stops). On drop, calls
 * onReorder with the new ordered place-id list so the parent can re-validate
 * and show the same confirm pattern as chat edits.
 */
export function SortableDayView({
  day,
  onReorder,
  highlightIds = [],
}: {
  day: Day;
  onReorder: (orderedPlaceIds: number[]) => void;
  highlightIds?: number[];
}) {
  const { palette } = useUI();
  const acts = [...day.activities].sort((a, b) => a.seq - b.seq);
  const ids = acts.map((a) => a.place_id);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  if (!acts.length) {
    return (
      <p style={{ ...TYPE.narrative, color: palette.textDim }}>
        No activities scheduled this day — ask the assistant to add something.
      </p>
    );
  }

  const onDragEnd = (e: DragEndEvent) => {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    const from = ids.indexOf(Number(active.id));
    const to = ids.indexOf(Number(over.id));
    onReorder(arrayMove(ids, from, to));
  };

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
      <SortableContext items={ids} strategy={verticalListSortingStrategy}>
        <div style={{ display: "grid", gridTemplateColumns: "36px 1fr", columnGap: SP.md }}>
          {acts.map((a, i) => (
            <Row key={a.place_id} id={a.place_id} index={i} last={i === acts.length - 1}
              tag={a.interest_tag} bg={palette.bg} activity={a}
              travel={i < acts.length - 1 ? travelLabel(acts[i], acts[i + 1]) : null}
              highlight={highlightIds.includes(a.place_id)} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}

function Row({ id, index, last, tag, bg, travel, highlight, activity }: {
  id: number; index: number; last: boolean; tag: string; bg: string;
  travel: string | null; highlight: boolean; activity: Day["activities"][number];
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  return (
    <>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ width: 32, height: 32, borderRadius: "50%", zIndex: 1, display: "grid", placeItems: "center",
                      ...TYPE.small, fontWeight: 600, color: "#F1F3F0", background: tagColor(tag),
                      border: `2px solid ${bg}` }}>{index + 1}</div>
        {!last && <div style={{ flex: 1, width: 2, marginTop: 2, borderRadius: 2, background: HARBOR }} />}
      </div>
      <div ref={setNodeRef} {...attributes} {...listeners}
        style={{ paddingBottom: SP.md, transform: CSS.Transform.toString(transform), transition,
                 opacity: isDragging ? 0.6 : 1, cursor: "grab", touchAction: "none" }}>
        <ActivityCard activity={activity} highlight={highlight} />
        {travel && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, minHeight: 22,
                        marginTop: -6, marginBottom: 6, paddingLeft: 2 }}>
            <span style={{ width: 5, height: 5, borderRadius: "50%", background: HARBOR, flexShrink: 0 }} />
            <span style={{ ...TYPE.small, color: HARBOR, fontWeight: 500 }}>{travel}</span>
          </div>
        )}
      </div>
    </>
  );
}

/** Duration-based travel hint (cached travel times aren't in the day payload). */
function travelLabel(a: Activity, b: Activity): string {
  const gap = Math.max(0, toMin(b.start_time) - toMin(a.end_time));
  if (gap <= 0) return "next stop";
  if (gap < 60) return `${Math.round(gap)} min to next stop`;
  const h = Math.floor(gap / 60), m = Math.round(gap % 60);
  return m ? `${h} h ${m} min to next stop` : `${h} h to next stop`;
}

function toMin(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return (h || 0) * 60 + (m || 0);
}
