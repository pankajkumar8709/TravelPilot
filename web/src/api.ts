/** Typed API client. Base URL: dev proxy '/api', prod VITE_API_BASE. */

const BASE = (import.meta.env.VITE_API_BASE as string) || "/api";

export interface Activity {
  place_id: number;
  name: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  cost: number;
  interest_tag: string;
  seq: number;
  lat: number;
  lon: number;
  backups: number[];
  image_url?: string;
}

export interface Suggestion {
  type: "food" | "stay";
  time_window: string;
  place_id: number;
  place_name: string;
  rank: number;
  lat: number;
  lon: number;
  website: string;
}

export interface Day {
  day_index: number;
  date: string;
  start_time: string;
  end_time: string;
  activities: Activity[];
  suggestions: Suggestion[];
}

export interface Diff {
  added: { place_id: number; name: string; start_time: string; end_time: string; cost: number; interest_tag: string }[];
  removed: { place_id: number; name: string; start_time: string; end_time: string; cost: number; interest_tag: string }[];
  modified: { place_id: number; name: string; from: string; to: string }[];
  stability: number;
  day_index: number;
  disrupted_place_id: number;
}

export interface Change {
  id: number;
  trip_id: number;
  status: string;
  reason: string;
  trigger: string;
  diff: Diff;
}

export interface Trip {
  id: number;
  destination: string;
  start_date: string;
  end_date: string;
  budget_total: number;
  currency: string;
  interests: string[];
  hotel_place_id: number | null;
  days: Day[];
  pending_changes: Change[];
}

export interface Place {
  id: number;
  name: string;
  lat: number;
  lon: number;
  category: string;
  interest_tag: string;
  opening_hours: string;
  avg_visit_minutes: number;
  cost: number;
  website: string;
}

export interface Amenity {
  id: number;
  name: string;
  lat: number;
  lon: number;
  type: string;
}

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export const api = {
  health: () => fetch(`${BASE}/health`).then(j<{ status: string; mockLLM: boolean; places: number }>),
  places: () => fetch(`${BASE}/places`).then(j<Place[]>),
  placesSearch: (q: string) => fetch(`${BASE}/places/search?q=${encodeURIComponent(q)}`).then(j<{ id: number; name: string; category: string; interest_tag: string }[]>),
  amenities: () => fetch(`${BASE}/amenities`).then(j<Amenity[]>),
  createTrip: (body: {
    destination: string; start_date: string; end_date: string;
    budget_total: number; currency: string; interests: string[]; hotel_place_id?: number | null;
    start_time_day1?: string; pace?: string; group_size?: number;
  }) => fetch(`${BASE}/trips`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  }).then(j<Trip>),
  getTrip: (id: number) => fetch(`${BASE}/trips/${id}`).then(j<Trip>),
  budget: (id: number, target?: string) =>
    fetch(`${BASE}/trips/${id}/budget${target ? `?target_currency=${target}` : ""}`).then(
      j<{ currency: string; per_day: { day_index: number; cost: number }[]; total: number; budget_total: number; over_budget: boolean }>,
    ),
  inject: (body: { trip_id: number; day_index: number; disrupted_place_id: number; trigger: string; reason?: string }) =>
    fetch(`${BASE}/disruptions/inject`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(j<Change>),
  confirm: (tripId: number, cid: number) =>
    fetch(`${BASE}/trips/${tripId}/changes/${cid}/confirm`, { method: "POST" }).then(j<{ status: string; stability: number }>),
  reject: (tripId: number, cid: number) =>
    fetch(`${BASE}/trips/${tripId}/changes/${cid}/reject`, { method: "POST" }).then(j<{ status: string }>),
  nl: (body: { trip_id: number; question: string; lang?: string }) =>
    fetch(`${BASE}/nl/query`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(j<{ intent: string; slots: Record<string, string>; answer: string; degraded: boolean }>),
  chatAdd: (body: { trip_id: number; place_query: string; day_index?: number | null; lang?: string }) =>
    fetch(`${BASE}/chat/add`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(j<Change>),
  chatMove: (body: { trip_id: number; place_id: number; to_day_index: number; lang?: string }) =>
    fetch(`${BASE}/chat/move`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(j<Change>),
  chatReorder: (body: { trip_id: number; day_index: number; ordered_place_ids: number[] }) =>
    fetch(`${BASE}/chat/reorder`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(j<Change>),
  share: (id: number) => fetch(`${BASE}/trips/${id}/share`).then(j<{ share_id: string; read_only: boolean }>),
};
