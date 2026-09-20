import { DndContext, closestCenter, PointerSensor, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Day } from "../api";
import { SP, TYPE, tagColor, ACCENT } from "../theme";
import { useUI } from "../ui-context";
import { ActivityCard } from "./ActivityCard";

/**
 * Drag-to-reorder day view. On drop, calls onReorder with the new ordered
 * place-id list so the parent can re-validate (travel-time re-check) and show
 * the same confirm pattern as chat edits.
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
    return <p style={{ ...TYPE.body, color: palette.textDim }}>No activities scheduled this day.</p>;
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
              tag={a.interest_tag} bg={palette.bg}>
              <ActivityCard activity={a} highlight={highlightIds.includes(a.place_id)} />
            </Row>
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}

function Row({ id, index, last, tag, bg, children }: {
  id: number; index: number; last: boolean; tag: string; bg: string; children: React.ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  return (
    <>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ width: 32, height: 32, borderRadius: "50%", zIndex: 1, display: "grid", placeItems: "center",
                      ...TYPE.small, fontWeight: 800, color: "#0F1117", background: tagColor(tag),
                      border: `2px solid ${bg}` }}>{index + 1}</div>
        {!last && <div style={{ flex: 1, width: 3, marginTop: 2, borderRadius: 2,
                                background: `linear-gradient(${tagColor(tag)}, ${ACCENT})` }} />}
      </div>
      <div ref={setNodeRef} {...attributes} {...listeners}
        style={{ paddingBottom: SP.md, transform: CSS.Transform.toString(transform), transition,
                 opacity: isDragging ? 0.6 : 1, cursor: "grab", touchAction: "none" }}>
        {children}
      </div>
    </>
  );
}
