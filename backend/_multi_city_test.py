"""Temp harness: ingest + generate trips across many cities, verify quality.

Uses the HTTP API (the exact path the UI takes). Writes MULTI_CITY_RESULTS.md.
Run from backend/:  .venv/Scripts/python.exe _multi_city_test.py
"""
import json
import sys
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"

CITIES = [
    # (destination, already_cached?)
    ("Varanasi", False), ("Kolkata", False), ("Chennai", False),
    ("Hyderabad", False), ("Goa", False), ("Udaipur", False),
    ("Amritsar", False), ("Kochi", False), ("Mysuru", False),
    ("Aurangabad", False), ("Shimla", False),
    # cached ones for the completeness check
    ("Delhi", True), ("Jaipur", True), ("Mumbai", True), ("Ranchi", True),
]


def post(path, body, timeout=300):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode()[:120]}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


rows = []
for dest, cached in CITIES:
    t0 = time.time()
    prep, err = post("/cities/prep", {"destination": dest})
    t_prep = time.time() - t0
    if err or not prep or not prep.get("ready"):
        rows.append((dest, "PREP FAIL", t_prep, err or str(prep)))
        print(f"X {dest}: prep failed in {t_prep:.0f}s -> {err}")
        continue

    t0 = time.time()
    trip, err = post("/trips", {
        "destination": dest, "start_date": "2026-10-01", "end_date": "2026-10-03",
        "budget_total": 8000, "currency": "INR",
        "interests": ["history", "culture", "food"],
        "start_time_day1": "09:00", "pace": "balanced", "group_size": 1,
    })
    t_gen = time.time() - t0
    if err or not trip or "days" not in trip:
        rows.append((dest, "GEN FAIL", t_prep + t_gen, err or str(trip)[:120]))
        print(f"X {dest}: generation failed -> {err}")
        continue

    days = trip["days"]
    acts = [a for d in days for a in d["activities"]]
    stops = len(acts)
    n_days = len(days)
    cost = sum(a["cost"] for a in acts)
    tags = {a["interest_tag"] for a in acts}
    food = sum(len(d["suggestions"]) for d in days)
    hotel = "Y" if trip.get("hotel_place_id") else "N"
    uniq = len({a["place_id"] for a in acts})
    ok = "OK" if (n_days == 3 and stops >= 9 and uniq == stops) else "WEAK"
    rows.append((dest, ok, t_prep, f"prep {prep['places']} places | {n_days}d/{stops} stops "
                                   f"(uniq {uniq}) | cost {cost:.0f} | tags {sorted(tags)} | "
                                   f"food/stay sugg {food} | hotel {hotel} | gen {t_gen:.0f}s"))
    print(f"{'OK' if ok=='OK' else '!'} {dest}: {n_days}d, {stops} stops, prep {t_prep:.0f}s, gen {t_gen:.0f}s")

print("\n===== RESULTS =====")
for r in rows:
    print(f"{r[1]:>9} | {r[0]:<12} | {r[3]}")

with open("../MULTI_CITY_RESULTS.md", "w", encoding="utf-8") as f:
    f.write("# Multi-city generation test\n\n")
    for r in rows:
        f.write(f"- **{r[0]}** — {r[1]} — {r[3]}\n")
