import { useState } from "react";
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, Tooltip } from "react-leaflet";
import type { Activity, Amenity, Day, Place, Suggestion } from "../api";
import { SP, tagColor, TYPE } from "../theme";
import { useUI } from "../ui-context";
import { t } from "../i18n";

/**
 * Phase 9 map view: the day's route as an ordered polyline, a distinct fixed
 * hotel marker, numbered activity markers colored by interest tag, food/stay
 * suggestion markers at their computed positions, and a toggleable amenity overlay.
 * All geometry comes from cached data (no live routing at runtime).
 */
export function MapView({
  day,
  hotel,
  amenities,
}: {
  day: Day;
  hotel: Place | null;
  amenities: Amenity[];
}) {
  const [showAmenities, setShowAmenities] = useState(false);
  const { lang, palette } = useUI();
  const acts = [...day.activities].sort((a, b) => a.seq - b.seq);

  const pts: [number, number][] = [];
  if (hotel) pts.push([hotel.lat, hotel.lon]);
  acts.forEach((a) => pts.push([a.lat, a.lon]));

  const center: [number, number] = acts.length
    ? [acts[0].lat, acts[0].lon]
    : hotel
    ? [hotel.lat, hotel.lon]
    : [48.8566, 2.3522];

  const foodSugs = day.suggestions.filter((s) => s.type === "food");
  const staySugs = day.suggestions.filter((s) => s.type === "stay").slice(0, 1);

  return (
    <div style={{ position: "relative", height: 420, borderRadius: 12, overflow: "hidden", border: `1px solid ${palette.border}` }}>
      <button
        onClick={() => setShowAmenities((v) => !v)}
        style={{
          position: "absolute", zIndex: 500, top: SP.sm, right: SP.sm,
          ...TYPE.small, padding: "6px 12px", borderRadius: 8, cursor: "pointer",
          background: showAmenities ? palette.accent : palette.surface,
          color: showAmenities ? palette.accentText : palette.text, border: `1px solid ${palette.border}`,
        }}
      >
        {showAmenities ? t("hide_amenities", lang) : t("show_amenities", lang)}
      </button>

      <MapContainer center={center} zoom={13} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; OpenStreetMap'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {pts.length >= 2 && <Polyline positions={pts} pathOptions={{ color: palette.accent, weight: 4, opacity: 0.8 }} />}

        {hotel && (
          <CircleMarker center={[hotel.lat, hotel.lon]} radius={11}
            pathOptions={{ color: "#fff", weight: 2, fillColor: tagColor("hotel"), fillOpacity: 1 }}>
            <Tooltip permanent direction="top">🏨 {hotel.name}</Tooltip>
          </CircleMarker>
        )}

        {acts.map((a: Activity, i) => (
          <CircleMarker key={a.place_id} center={[a.lat, a.lon]} radius={13}
            pathOptions={{ color: "#0F1117", weight: 2, fillColor: tagColor(a.interest_tag), fillOpacity: 1 }}>
            <Tooltip permanent direction="center" className="num-tip">{i + 1}</Tooltip>
            <Popup>
              <b>{a.name}</b><br />{a.start_time}–{a.end_time} · {a.interest_tag}
            </Popup>
          </CircleMarker>
        ))}

        {foodSugs.map((s: Suggestion) => (
          <CircleMarker key={`f${s.place_id}`} center={[s.lat, s.lon]} radius={7}
            pathOptions={{ color: "#fff", weight: 1, fillColor: tagColor("food"), fillOpacity: 0.9, dashArray: "3" }}>
            <Popup>🍽 <b>{s.place_name}</b><br />{s.time_window}{s.website ? <><br /><a href={s.website} target="_blank">{t("view_book", lang)}</a></> : null}</Popup>
          </CircleMarker>
        ))}

        {staySugs.map((s: Suggestion) => (
          <CircleMarker key={`s${s.place_id}`} center={[s.lat, s.lon]} radius={9}
            pathOptions={{ color: "#fff", weight: 2, fillColor: "#A78BFA", fillOpacity: 0.95 }}>
            <Popup>🛏 suggested stay: <b>{s.place_name}</b></Popup>
          </CircleMarker>
        ))}

        {showAmenities &&
          amenities.map((am) => (
            <CircleMarker key={`a${am.id}`} center={[am.lat, am.lon]} radius={5}
              pathOptions={{ color: "#94A3B8", weight: 1, fillColor: "#94A3B8", fillOpacity: 0.7 }}>
              <Popup>{am.type}: {am.name}</Popup>
            </CircleMarker>
          ))}
      </MapContainer>
    </div>
  );
}
