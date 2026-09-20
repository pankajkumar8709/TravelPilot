# Phase 10 — Demo Hardening

Goal: nothing about live conditions can sink the demo.

## S3 data lake (the "why S3" answer) — ✅ built
Raw Overpass/ORS responses are written to S3 (`raw/<source>/<city>/<ts>.json`)
BEFORE they're transformed into RDS — `backend/app/services/datalake.py`, wired
into `ingest.py` right after the Overpass fetch.

**The architectural justification (say this if a judge asks "why S3?"):**
S3 is the immutable raw landing zone; RDS is the queryable serving layer built
from it. If we change how we parse OSM tags, we can re-transform from the S3 raw
copy without re-hitting the rate-limited Overpass/ORS APIs. It's a real
lake→warehouse split, not a checkbox.

Setup (once, in your account):
```
set DATA_LAKE_BUCKET=travelpilot-datalake-<unique-suffix>
set AWS_PROFILE=travelpilot
python -m app.scripts.setup_datalake      # creates the private bucket
python -m app.scripts.ingest --city "Paris" ...   # now also lands raw JSON in S3
```
No bucket set → ingest skips S3 gracefully and still loads RDS.

## Recorded backup video (YOUR task — script below)
Record a full clean run end-to-end, saved offline, in case live fails.

**3-minute run order to record:**
1. Setup form → Paris, 3 days, €400, interests culture/history/outdoor → Generate
2. Dashboard appears — day tabs, activity cards, map with route + numbered markers
3. Point out a food suggestion pin + the stay pin (time-anchored, not near hotel)
4. **The money shot:** press 🌧 weather-disrupt on an outdoor activity
   → diff view slides in: REMOVED (red) / ADDED (green) + plain-language reason
   → call out the **plan-stability %** and that ONLY that slice changed
5. Confirm the change → dashboard + map re-render with the repaired day
6. Ask the NL box: "what should I do tomorrow morning?" → grounded answer
7. Show budget rollup (per-day + total)

Save the recording somewhere offline-accessible (not only in the cloud).

## Pre-demo checklist (run on the DEPLOYED env, not localhost)
- [ ] Record the clean run above; save offline
- [ ] Confirm S3 receives raw ingest JSON (check the bucket after an ingest)
- [ ] Full dry run of the Phase 11 demo script TWICE on the deployed URL
- [ ] Check AWS credit balance isn't near exhaustion mid-demo
- [ ] Re-seed a clean demo trip right before presenting: `python -m app.scripts.seed && python -m app.scripts.seed_demo_trip`
- [ ] Verify `/health` on the deployed backend returns 200
- [ ] Confirm the browser tab you'll present has the trip already loaded (no cold generate on stage)

## Fallback ladder (if something breaks live)
1. Live deployed app (primary)
2. Local stack on your laptop (uvicorn + npm dev) — identical, no AWS dependency
3. The recorded video (last resort)

## Exit criterion
You could lose internet five minutes before presenting and still have something
to show (local stack + recorded video). ✅ once the video is recorded.
