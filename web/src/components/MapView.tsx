import { useState } from "react";
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, Tooltip } from "react-leaflet";
import type { Activity, Amenity, Day, DayRoute, Place, Suggestion } from "../api";
import { SP, tagColor, TYPE, HARBOR } from "../theme";
import { useUI } from "../ui-context";
import { t } from "../i18n";

/**
 * Phase 9 map view: the day's route as an ordered polyline, a distinct fixed
 * hotel marker, numbered activity markers colored by interest tag, food/stay
 * suggestion markers at their computed positions, and a toggleable amenity
 * overlay. Route geometry comes from the backend's cached `routes` table
 * (ORS Directions on cache miss, straight-line fallback offline). The map
 * itself defaults to a dark Ink style regardless of app mode.
 */
export function MapView({
  day,
  hotel,
  amenities,
  route,
}: {
  day: Day;
  hotel: Place | null;
  amenities: Amenity[];
  route: DayRoute | null;
}) {
  const [showAmenities, setShowAmenities] = useState(false);
  const { lang, palette } = useUI();
  const acts = [...day.activities].sort((a, b) => a.seq - b.seq);

  // Basemap tiles. CARTO's dark basemap now requires a free API key; without
  // one we fall back to keyless OSM tiles rendered dark via a CSS filter
  // (main.tsx .tp-tiles-filtered) — no vendor account needed.
  const cartoKey = import.meta.env.VITE_CARTO_API_KEY as string | undefined;

  // straight-line hop route (always available)
  const pts: [number, number][] = [];
  if (hotel) pts.push([hotel.lat, hotel.lon]);
  acts.forEach((a) => pts.push([a.lat, a.lon]));

  // routed legs from the backend: [lon, lat] -> Leaflet's [lat, lon]
  const legLines: [number, number][][] = (route?.legs ?? [])
    .map((leg) => leg.geometry.map(([lon, lat]) => [lat, lon] as [number, number]))
    .filter((line) => line.length >= 2);

  const center: [number, number] = acts.length
    ? [acts[0].lat, acts[0].lon]
    : hotel
    ? [hotel.lat, hotel.lon]
    : [48.8566, 2.3522];

  const foodSugs = day.suggestions.filter((s) => s.type === "food");
  const staySugs = day.suggestions.filter((s) => s.type === "stay").slice(0, 1);

  return (
    <div style={{ position: "relative", height: 440, borderRadius: 12, overflow: "hidden", border: `1px solid ${palette.border}` }}>
      <button
        onClick={() => setShowAmenities((v) => !v)}
        aria-pressed={showAmenities}
        style={{
          position: "absolute", zIndex: 500, top: SP.sm, right: SP.sm,
          ...TYPE.small, minHeight: 36, padding: "7px 12px", borderRadius: 8, cursor: "pointer",
          background: showAmenities ? HARBOR : "#10151F",
          color: "#F1F3F0", border: "1px solid #FFFFFF24",
        }}
      >
        {showAmenities ? t("hide_amenities", lang) : t("show_amenities", lang)}
      </button>

      <MapContainer center={center} zoom={13} style={{ height: "100%", width: "100%", background: "#10151F" }}
        className={cartoKey ? undefined : "tp-tiles-filtered"}>
        <TileLayer
          attribution={cartoKey
            ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
            : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}
          url={cartoKey
            ? `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?apiKey=${cartoKey}`
            : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"}
        />

        {/* straight-line hops — underlay, only visible where a routed leg is missing */}
        {pts.length >= 2 && legLines.length === 0 && (
          <Polyline positions={pts} pathOptions={{ color: HARBOR, weight: 3, opacity: 0.5, dashArray: "6 8" }} />
        )}

        {/* real walked-route polylines from the cached/ORS geometry */}
        {legLines.map((line, i) => (
          <Polyline key={i} positions={line} pathOptions={{ color: HARBOR, weight: 4, opacity: 0.9 }} />
        ))}

        {hotel && (
          <CircleMarker center={[hotel.lat, hotel.lon]} radius={10}
            pathOptions={{ color: "#F1F3F0", weight: 2, fillColor: tagColor("hotel"), fillOpacity: 1 }}>
            <Tooltip permanent direction="top" className="num-tip">Hotel · {hotel.name}</Tooltip>
          </CircleMarker>
        )}

        {acts.map((a: Activity, i) => (
          <CircleMarker key={a.place_id} center={[a.lat, a.lon]} radius={12}
            pathOptions={{ color: "#10151F", weight: 2, fillColor: tagColor(a.interest_tag), fillOpacity: 1 }}>
            <Tooltip permanent direction="center" className="num-tip">{i + 1}</Tooltip>
            <Popup>
              <b>{a.name}</b><br />{a.start_time}–{a.end_time} · {a.interest_tag}
            </Popup>
          </CircleMarker>
        ))}

        {foodSugs.map((s: Suggestion) => (
          <CircleMarker key={`f${s.place_id}`} center={[s.lat, s.lon]} radius={7}
            pathOptions={{ color: "#F1F3F0", weight: 1, fillColor: tagColor("food"), fillOpacity: 0.95, dashArray: "3" }}>
            <Popup>
              <b>{s.place_name}</b><br />{s.time_window}
              {s.website ? <><br /><a href={s.website} target="_blank" rel="noreferrer">{t("view_book", lang)}</a></> : null}
            </Popup>
          </CircleMarker>
        ))}

        {staySugs.map((s: Suggestion) => (
          <CircleMarker key={`s${s.place_id}`} center={[s.lat, s.lon]} radius={9}
            pathOptions={{ color: "#F1F3F0", weight: 2, fillColor: HARBOR, fillOpacity: 0.95 }}>
            <Popup>
              suggested stay: <b>{s.place_name}</b>
            </Popup>
          </CircleMarker>
        ))}

        {showAmenities &&
          amenities.map((am) => (
            <CircleMarker key={`a${am.id}`} center={[am.lat, am.lon]} radius={5}
              pathOptions={{ color: "#9CA5B4", weight: 1, fillColor: "#9CA5B4", fillOpacity: 0.7 }}>
              <Popup>{am.type}: {am.name}</Popup>
            </CircleMarker>
          ))}
      </MapContainer>
    </div>
  );
}
