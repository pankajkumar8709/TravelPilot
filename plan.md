# TravelPilot — Detailed Build Plan

**Stack:** FastAPI (App Runner) · React + TypeScript (Amplify) · RDS Postgres (SQLAlchemy) · Bedrock (boto3) · EventBridge → SQS → Lambda (disruption path) · S3 (raw data lake)

**Data sourcing principle:** Reference data (places, hours, travel times) is fetched once during dev and cached in RDS — the app never calls an external API for this at runtime. Disruption-signal data (weather, flight status) is the only category polled live.

---

## Phase 0 — Stack + Strategy Lock

**Goal:** Freeze every infrastructure decision before writing feature code, so no phase later gets derailed by a "wait, which database are we using" conversation.

**What it includes:**
- Final commitment to the stack above — no swapping mid-build
- Repo structure agreed across the team (monorepo vs. split frontend/backend)
- AWS account access, IAM roles, and billing alerts set up for every teammate
- Environment variable / secrets strategy decided (AWS Secrets Manager or `.env` + App Runner config)

**Implementation checklist:**
- [ ] Create App Runner service (backend) and Amplify app (frontend) shells — even empty, deployed "hello world" versions
- [ ] Provision RDS Postgres instance, confirm SQLAlchemy can connect from local + App Runner
- [ ] Confirm Bedrock model access is enabled in your AWS region (not all regions/models are available by default — check this first, it's a common day-1 blocker)
- [ ] Set up EventBridge, SQS, and a placeholder Lambda, confirm a test event flows end to end
- [ ] Agree on branching strategy and who owns which phase

**Exit criteria:** Every AWS service in the stack has been touched once, by at least one deployed "it works" test — not just provisioned in the console.

---

## Phase 1 — 45-Minute Wireframe Pass

**Goal:** Lock the visual and information architecture fast, so Phase 9 (UI polish) has a target instead of being designed from scratch under time pressure.

**What it includes:**
- Low-fidelity wireframes (paper, Figma, or even boxes-and-text in a doc) for the four core screens:
  1. **Setup form** — destination, dates, budget, interests
  2. **Day view** — the itinerary for a single day, with activities in sequence
  3. **Dashboard** — the full-trip summary (final deliverable screen)
  4. **Diff view** — before/after comparison when a disruption triggers a rebuild
- A locked design system: one type scale, one accent color per interest tag (e.g. food = coral, culture = purple, outdoor = teal), one reusable card pattern for activities

**Implementation checklist:**
- [ ] Sketch all four screens — don't skip the diff view, it's your highest-leverage screen later and needs a slot in the plan now
- [ ] Decide the card pattern for an "activity" (fields: name, time, duration, cost, location tag) — reuse this exact shape everywhere it appears
- [ ] Pick 4–5 interest tags and assign each a fixed color — used consistently across day view, dashboard, and diff view
- [ ] Write down the type scale (heading sizes, body size) so no one improvises later

**Exit criteria:** A shared reference (image or doc) that anyone on the team can glance at and know what screen they're building toward.

---

## Phase 2 — Walking Skeleton

**Goal:** Get one complete, hardcoded path deployed live — frontend to backend to database and back — before any real logic exists. From this point on, you always have something demoable, even if it's fake data.

**What it includes:**
- A single hardcoded itinerary (2–3 days, fabricated activities) stored in RDS
- Setup form submits → hits FastAPI → reads the hardcoded trip from RDS → renders on the dashboard
- Full deploy pipeline working: frontend on Amplify talking to backend on App Runner talking to RDS, all in the actual AWS environment (not localhost)

**Implementation checklist:**
- [ ] Define the core Postgres schema early (trips, days, activities, bookings) even though it'll evolve in Phase 3
- [ ] Seed one hardcoded trip row via a script or raw SQL
- [ ] Build the FastAPI endpoint `GET /trips/{id}` returning that seeded trip as JSON
- [ ] Build the React dashboard screen that renders that JSON into the Phase 1 wireframe layout
- [ ] Confirm the whole loop works from the deployed Amplify URL, not just localhost

**Exit criteria:** You can open the live Amplify URL, and see a real (if fake) itinerary rendered end-to-end through the real AWS pipeline.

---

## Phase 3 — State Model + Real Reference-Data Ingestion

**Goal:** Replace the hardcoded seed data with real place data for your chosen destination, fetched once and cached — the single biggest reliability decision in the whole build, because it means a live API outage on demo day cannot touch you.

**What it includes:**
- A one-time ingestion script (run during development, never at runtime) that:
  1. Hits the **Overpass API** for points of interest in your chosen destination (restaurants, museums, parks, etc., with coordinates and opening hours where available)
  2. Also queries Overpass for utility amenities relevant to a traveler on the move — public washrooms (`amenity=toilets`), ATMs, pharmacies — tagged separately from "activities" so the map view can toggle them on independently
  3. Hits **Nominatim** for geocoding anything Overpass doesn't resolve cleanly
  4. Hits **OpenRouteService** for pairwise travel times *and* route geometry (the actual path polyline between two points, not just a duration number) between every relevant pair of points
  5. Writes all of this into RDS Postgres as your permanent reference dataset
- The finalized Postgres schema: `places` (id, name, coords, category, opening_hours), `amenities` (id, name, coords, type — toilets/ATM/pharmacy), `travel_times` (from_id, to_id, duration_minutes, mode), `routes` (from_id, to_id, geometry — polyline for map rendering), `trips`, `days`, `activities`, `bookings`

**Implementation checklist:**
- [ ] Pick your demo destination carefully — a well-mapped city (OSM coverage varies a lot city to city)
- [ ] Write and run the Overpass ingestion script; manually spot-check a handful of results for sanity (wrong coordinates or missing hours will surface later as scheduling bugs)
- [ ] Extend the same script to pull amenity POIs (washrooms, ATMs, pharmacies) into their own table — these are never scheduled as activities, only shown as map overlays
- [ ] Write and run the ORS pairwise travel-time script, requesting route geometry alongside duration; cap the pair count if you have many places (2,000 requests/day free tier — batch smartly)
- [ ] Load everything into RDS; write a quick script to confirm row counts and spot-check joins
- [ ] At this point, delete or disable any code path that calls Overpass/ORS at runtime — the app should only ever read its own database from here on

**Exit criteria:** RDS contains a real, sizeable set of places and travel times for your destination, and the app never makes an external reference-data call while running.

---

## Phase 4 — Itinerary Generation Engine

**Goal:** Turn user constraints into an actual optimized day-by-day plan over the real data. This is the first genuine "wow" moment in the build.

**What it includes:**
- A greedy scheduling algorithm (not an LLM doing arithmetic) that, given a day's time window, a budget slice, and a set of candidate places filtered by interest tags:
  1. Filters candidates by opening hours overlapping the day's window
  2. Picks a starting point (e.g. nearest to the hotel) and greedily selects the next nearest unvisited candidate that fits the remaining time and budget
  3. Repeats until the day's time/budget is filled or candidates run out
  4. Assigns concrete start/end times to each chosen activity, accounting for travel time between consecutive stops
- Bedrock's role here is narrow and specific: given the constraint set, it decides *which interest tags and place categories* to prioritize and in what proportion — the actual sequencing math stays deterministic in Python
- **Time-anchored food and stay suggestions** — once every activity has a concrete start/end time (step 4 above), the scheduler makes a second pass that doesn't add anything to the itinerary, it just attaches suggestions to specific moments in it:
  1. Walk the day's timeline looking for meal windows — a gap around midday with no activity (lunch) and the period after the last activity ends, roughly 7–10pm (dinner). If the day starts at 2pm with activities running into the evening, the dinner window is computed from *when the last activity actually ends*, not a fixed clock time.
  2. At each meal window, take the estimated location at that point in the route (the coordinates of whichever activity precedes the gap) and query the cached `places` table (food category) sorted by travel time from that point, filtered to places likely open in that window
  3. Surface the top 2–3 as suggestions attached to that time slot — not scheduled, not blocking, just offered
  4. For the **stay**, do the same at end-of-day: take the location of the last activity, and rank cached hotels by a combined score of proximity to that end-of-day point *and* proximity to tomorrow's first planned activity (so the suggestion doesn't create a bad next-day commute)
  5. Each suggestion carries through the external-link data captured in Phase 3 (website tag or constructed search URL) so it's ready for the "view & book" redirect

**Implementation checklist:**
- [ ] Write the greedy nearest-neighbor scheduler as a standalone, testable Python function (input: candidate places + constraints, output: ordered day plan)
- [ ] Wire Bedrock to take the user's free-text interests/budget and translate them into structured filter parameters (which categories, roughly what daily budget split) for the scheduler
- [ ] Run the scheduler across all trip days, respecting per-day time windows and the total trip budget
- [ ] Store the generated itinerary back into the `days`/`activities` tables
- [ ] Write the meal-window detection function: given a day's ordered activities with times, return the gaps that qualify as lunch/dinner windows and the location to search from at each
- [ ] Write the ranking query for food suggestions: cached food places, sorted by travel time from the gap's location, filtered by likely-open-in-window
- [ ] Write the end-of-day stay ranking query: cached hotels, scored on proximity to both the last activity of today and the first activity of tomorrow
- [ ] Store suggestions as their own lightweight record (`suggestions`: day_id, type — food/stay, time_window, place_id, rank) separate from `activities`, since they're never scheduled, only offered

**Exit criteria:** Given a destination, dates, budget, and interests, the app produces a full day-by-day itinerary from real place data — not hardcoded, not random — and each day carries 2–3 time-appropriate food suggestions plus an end-of-day stay suggestion, each grounded in the actual computed arrival time and location, not a generic "near downtown" guess.

---

## Phase 5 — Conflict/Validation Engine

**Goal:** Catch itinerary problems before they reach the user — overlapping activities, infeasible travel times, or budget overruns.

**What it includes:**
- A validation pass run after every itinerary generation or rebuild, checking:
  - Time overlaps between consecutive activities (including travel time buffer)
  - Activities scheduled outside their opening hours
  - Daily and total budget against the user's stated limit
- A structured list of "violations" the app can surface to the user or use to trigger a re-schedule

**Implementation checklist:**
- [ ] Write a validator function that walks each day's activity list in time order and checks: does activity N+1's start time account for travel time from activity N's location?
- [ ] Add opening-hours checks against the cached reference data
- [ ] Add a budget rollup check per day and for the whole trip
- [ ] Return violations as structured data (type, affected activity IDs, message) — not just a pass/fail flag, since Phase 7/9 need to explain *what* is wrong

**Exit criteria:** Feeding the validator a deliberately broken itinerary (overlapping times, over-budget) returns a clear, structured list of what's wrong.

---

## Phase 6 — Budget/Tracking Aggregation

**Goal:** Roll up costs across the trip. Deliberately kept thin — this is a supporting feature, not a differentiator, so don't over-invest here.

**What it includes:**
- Simple summation: cost per activity → cost per day → total trip cost
- A currency conversion step (if the user's budget is in a different currency than the destination's local prices) via **Frankfurter.app** or **exchangerate.host**

**Implementation checklist:**
- [ ] Add a `cost` field to each activity/booking record
- [ ] Write a simple aggregation endpoint: `GET /trips/{id}/budget` returning daily and total costs
- [ ] Add a currency conversion call (cache the rate for the session, don't call on every page load)

**Exit criteria:** The dashboard can show an accurate daily and total budget figure, in the user's preferred currency.

---

## Phase 7 — Disruption Handling

**Goal:** The centerpiece feature — detect a disruption and rebuild only what's affected, without depending on a real-world event actually occurring during your demo window.

**What it includes:**
- **Two triggers, deliberately, not one:**
  1. A real scheduled **EventBridge rule** polling **Open-Meteo** (weather) and **Amadeus Flight Status** for genuine changes relevant to the trip's dates/location
  2. A manual **"inject disruption" button** in the UI that fires the exact same downstream code path with a synthetic event — this is what you'll actually use live in front of judges, since you can't bet a demo on a real flight delay happening in a three-minute window
- The repair pipeline itself (triggered identically by either source):
  1. Identify which activities/bookings are causally affected by the disruption (not the whole itinerary)
  2. Re-run the Phase 4 scheduler *only* on the affected time window, holding everything else fixed
  3. Re-run the Phase 5 validator on the result
  4. Pull 1–2 precomputed backup alternates (same interest tag, same time window) if a direct replacement is needed
  5. Package the result as a diff (what changed, what stayed, why) for Phase 9 to render
- The event flow: EventBridge → SQS → Lambda → repair pipeline → written back to RDS as a *pending* change (not yet applied) until the user confirms

**Implementation checklist:**
- [ ] Build the EventBridge → SQS → Lambda plumbing for the scheduled poll (even if the poll rarely fires something real during dev, prove the pipeline works with a forced test event)
- [ ] Build the "inject disruption" UI control that POSTs a synthetic event through the identical Lambda entry point
- [ ] Write the "affected scope" identification logic — given a cancelled/changed activity or booking, which other activities in the same day are impacted (e.g. everything after it in the sequence)
- [ ] Reuse the Phase 4 scheduler and Phase 5 validator on just that scope
- [ ] At itinerary-generation time (Phase 4), precompute and store 1–2 backup candidates per activity so this step doesn't need a live search
- [ ] Store the proposed change as "pending" in RDS with a diff structure (added/removed/modified activities + a short reason string), separate from the "confirmed" itinerary state

**Exit criteria:** Pressing the inject-disruption button visibly changes only the affected slice of one day, produces a clear before/after diff with a stated reason, and does *not* touch the rest of the trip.

---

## Phase 8 — NL Interface via Bedrock

**Goal:** Let the user ask questions in plain language, without ever letting the model touch trip state directly.

**What it includes:**
- **Intent classification + slot extraction only** — Bedrock's job is to figure out *what the user is asking* and extract structured parameters (date, activity name, location reference), never to read or write the database itself
- A fixed set of backend intents it can route to, each a deterministic query against RDS:
  - "What should I do tomorrow morning?" → filter tomorrow's activities by time-of-day
  - "Can I fit this into today's schedule?" → run the Phase 5 validator against a hypothetical insertion
  - "Which activities are close to my hotel?" → sort cached travel-time data from the hotel's location
  - "What happens if this booking is cancelled?" → run the Phase 7 repair pipeline in dry-run mode (compute the diff, don't apply it) and describe the result in natural language

**Implementation checklist:**
- [ ] Define the fixed intent schema (intent name + required slots) and prompt Bedrock to output that schema in JSON, nothing else
- [ ] Write one deterministic backend handler per intent — each just a normal SQL query or a call into existing Phase 4/5/7 logic
- [ ] Have Bedrock take the handler's structured result and phrase it back in natural language for the response
- [ ] Explicitly test that a malformed or out-of-scope question fails gracefully (falls back to a generic "I can help with X, Y, Z" rather than guessing at random state changes)

**Exit criteria:** Each of the four sample questions from the brief returns a correct, natural-language answer grounded in real trip data — with zero direct model access to the database.

---

## Phase 9 — Diff/Dashboard UI Polish

**Goal:** This is the highest-leverage screen for judges — build it last, on top of a system that already works, not as a design exercise in isolation.

**What it includes:**
- The final trip dashboard: daily itinerary, transportation, activities, estimated costs, important timings, backup options — all in the card pattern and color system locked in Phase 1
- The diff view: a clear before/after presentation of any pending disruption-triggered change, with the reason surfaced in plain language, and explicit confirm/reject controls
- A **map view**, toggle-able from both the dashboard and the day view, showing the day's plan spatially rather than as a list: the day's route drawn as an ordered polyline (using the cached geometry from Phase 3), a fixed, visually distinct marker for the hotel/stay, numbered markers for each activity in visit order colored by interest tag, and a toggleable overlay layer for utility amenities (washrooms, ATMs) so they're available on demand without cluttering the default view
- The map also plots the **time-anchored suggestions from Phase 4** at the correct point along the route: food markers appear near wherever the route actually is at the computed meal-window time (not clustered near the hotel by default), each labeled with its suggested time window (e.g. "dinner · ~8–10pm"); the end-of-day stay suggestion appears as a marker near the last activity, distinct from the fixed "current hotel" marker so the user can visually compare tonight's stay against tomorrow's plan. Clicking any food or stay marker opens the "view & book" redirect from the earlier external-link work.
- Polish pass on the day view and setup form to match

**Implementation checklist:**
- [ ] Build the dashboard screen against real (not mocked) data from Phases 3–6
- [ ] Build the diff view rendering the structure produced in Phase 7 (added/removed/modified + reason)
- [ ] Wire the confirm/reject buttons to actually apply or discard the pending change in RDS
- [ ] Build the map view component using a map tile layer (e.g. Amazon Location Service, or MapLibre + OSM tiles if simpler for a hackathon timeline) rendering the cached route geometry and amenity data from Phase 3 — no live routing calls at runtime, same reference-data caching principle as everything else
- [ ] Give the hotel/stay marker a distinct icon and z-order so it never gets visually lost among activity markers
- [ ] Render the `suggestions` records from Phase 4 as their own marker type — food markers positioned at their computed location, each with a small time-window label; the end-of-day stay suggestion visually distinct from the current-hotel marker
- [ ] Wire each suggestion marker's click to the external "view & book" link
- [ ] Add a simple layer toggle for washrooms/amenities, off by default
- [ ] When a disruption changes the day's activities, make sure the map view re-renders the updated route too — it reads from the same day/activity state as the list view, so this should be close to free if wired correctly
- [ ] Pass over every screen once for consistency — spacing, type scale, color usage — against the Phase 1 lock

**Exit criteria:** A judge can look at the dashboard, diff view, and map view without any narration and understand what the trip looks like, where it happens, and what just changed.

---

## Phase 10 — Demo Hardening

**Goal:** Make sure nothing about live conditions can sink the demo.

**What it includes:**
- A recorded backup video of a full successful run-through, in case of live failure (network, AWS hiccup, etc.)
- An S3 bucket storing the raw Overpass/ORS/Amadeus fetch results from Phase 3, positioned as a "data lake" layer feeding RDS — this is a real architectural justification, not a checkbox, and gives you a genuine answer if a judge asks "why S3"

**Implementation checklist:**
- [ ] Record a full clean demo run end-to-end, save it somewhere accessible offline
- [ ] Route the Phase 3 ingestion script's raw API responses into S3 before they're transformed and loaded into RDS
- [ ] Do a full dry run of the actual demo script (see Phase 11) at least twice, on the deployed environment, not localhost
- [ ] Check AWS free-tier/credit limits aren't at risk of being exhausted mid-demo

**Exit criteria:** You could lose internet access five minutes before presenting and still have something to show.

---

## Phase 11 — Pitch Prep

**Goal:** Make sure the technical work actually lands with judges in the time given.

**What it includes:**
- A one-sentence problem statement
- A one-sentence positioning line: disruption-handling, not just generation — this is the sentence that separates you from every other itinerary generator in the room
- One technical "flex" line — a specific, defensible technical choice (e.g. "we do minimal-diff repair instead of full regeneration, which is a metric researchers are now benchmarking on")
- A timed rehearsal of the full demo

**Implementation checklist:**
- [ ] Write and memorize the problem sentence and the differentiator sentence — don't read them off a slide
- [ ] Pick one technical flex line and make sure whoever says it can field a follow-up question on it
- [ ] Time the full demo at least twice; trim if it runs long
- [ ] Assign who talks during which phase of the demo if presenting as a team

**Exit criteria:** The full pitch, including the live demo, fits comfortably inside your allotted time with room for one follow-up question.

---

## Phase 12 — Differentiators (build in this priority order, time permitting)

**Goal:** Layer in the features that separate this from a generic itinerary generator, in order of effort-to-impact ratio.

1. **Confirmation-before-apply** — pending changes from Phase 7 require explicit user confirmation before writing to the confirmed itinerary. *(Already required by the Phase 7/9 design above — verify it's actually enforced, not just visual.)*
2. **Diff view** — already built in Phase 9; make sure it's the screen you linger on in the demo.
3. **Precomputed backups** — already required by Phase 7; confirm every activity in the generated itinerary actually has 1–2 stored alternates, not just the ones you tested.
4. **Minimal-diff repair** — already the core design of Phase 7; the differentiator is making sure it's *visibly* minimal in the demo (only 1–2 activities change, not the whole day).
5. **Plan-stability score** — a simple metric: percentage of original activities that survive a rebuild unchanged. Compute and display it after a disruption is applied — cheap to add, and it's the exact metric current academic benchmarks use, which is a strong talking point if asked about rigor.
6. **Compound disruptions** — handle two simultaneous disruptions (e.g. a cancelled activity and a weather closure) as one coherent repair rather than two sequential overwrites. Only attempt this once single-disruption repair is solid.
7. **Proactive monitoring surfaced to the user** — rather than only reacting when the user opens the app, surface a notification-style alert when the scheduled EventBridge poll detects something real. Build this last — it's the least essential to a working demo.