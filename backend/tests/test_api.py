"""End-to-end backend smoke test (in-process, no live server -> no stale-server trap).

Exercises the full walking-skeleton -> generation -> disruption -> confirm loop
against a fresh SQLite DB, using the mock LLM (offline-safe).

Run:  cd backend && python -m pytest -v tests/test_api.py
"""
from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture()
def client():
    # fresh temp DB per run so state never leaks between test runs
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"
    os.environ["USE_MOCK_LLM"] = "true"

    # import AFTER env is set so settings pick it up
    import importlib
    import app.config as cfg
    importlib.reload(cfg)
    import app.db as dbmod
    importlib.reload(dbmod)
    import app.models  # noqa
    import app.scripts.seed as seedmod
    importlib.reload(seedmod)

    from fastapi.testclient import TestClient
    import app.services.trip_service as ts
    importlib.reload(ts)
    import app.main as mainmod
    importlib.reload(mainmod)

    seedmod.seed()
    with TestClient(mainmod.app) as c:
        yield c
    # Windows holds the SQLite file until the engine is disposed
    dbmod.engine.dispose()
    try:
        os.remove(path)
    except PermissionError:
        pass  # temp file; OS reclaims it — not an app concern


def test_full_flow(client):
    # health
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["places"] > 0

    # places seeded
    assert len(client.get("/places").json()) > 0

    # create + generate a 2-day Paris trip
    trip = client.post("/trips", json={
        "destination": "Paris", "start_date": "2026-09-25", "end_date": "2026-09-26",
        "budget_total": 300, "currency": "EUR", "interests": ["culture", "history", "food"],
    }).json()
    assert len(trip["days"]) == 2
    day1 = trip["days"][0]
    assert len(day1["activities"]) >= 2, "generation produced a real day plan"
    # Phase 4 suggestions attached
    assert any(s["type"] == "food" for s in day1["suggestions"])
    assert any(s["type"] == "stay" for s in day1["suggestions"])
    # Phase 7 backups precomputed
    assert isinstance(day1["activities"][0]["backups"], list)

    # budget rollup (Phase 6)
    b = client.get(f"/trips/{trip['id']}/budget").json()
    assert "total" in b and "per_day" in b
    # per-day entries exist for each day and total equals the sum of per-day costs
    assert len(b["per_day"]) == len(trip["days"])
    day_sum = round(sum(p["cost"] for p in b["per_day"]), 2)
    assert abs(b["total"] - day_sum) < 0.01, "total must equal sum of per-day costs"
    assert "over_budget" in b

    # inject a disruption on day 1's LAST activity (minimal change expected)
    day2_before = {a["place_id"] for a in trip["days"][1]["activities"]} if len(trip["days"]) > 1 else set()
    last = sorted(day1["activities"], key=lambda a: a["seq"])[-1]
    change = client.post("/disruptions/inject", json={
        "trip_id": trip["id"], "day_index": 1,
        "disrupted_place_id": last["place_id"], "trigger": "weather",
    }).json()
    assert change["status"] == "pending"
    diff = change["diff"]
    assert diff["removed"], "disrupted activity shows as removed"
    assert 0.0 <= diff["stability"] <= 100.0
    assert change["reason"]  # a plain-language reason exists

    # confirm applies it
    applied = client.post(f"/trips/{trip['id']}/changes/{change['id']}/confirm").json()
    assert applied["status"] == "applied"

    # disrupted place is gone after apply
    after = client.get(f"/trips/{trip['id']}").json()
    after_day1 = after["days"][0]
    assert last["place_id"] not in {a["place_id"] for a in after_day1["activities"]}

    # MINIMAL-DIFF: a day-1 disruption must NOT touch day 2 (the differentiator claim)
    if len(after["days"]) > 1:
        day2_after = {a["place_id"] for a in after["days"][1]["activities"]}
        assert day2_after == day2_before, "day 2 must be untouched by a day-1 disruption"

    # NL interface (Phase 8) — the plan's FOUR sample questions each route correctly,
    # and every answer is grounded in DB data (the model never touches trip state).
    q_expect = [
        ("what should I do tomorrow morning?", "day_plan"),
        ("which activities are close to my hotel?", "near_hotel"),
        ("what happens if this booking is cancelled?", "what_if_cancel"),
        ("can I fit this into today's schedule?", "fit_check"),
    ]
    for question, intent in q_expect:
        r = client.post("/nl/query", json={"trip_id": trip["id"], "question": question}).json()
        assert r["intent"] == intent, f"{question!r} -> {r['intent']} (expected {intent})"
        assert r["answer"], "every intent returns a natural-language answer"

    # graceful out-of-scope fallback (never guesses a random state change)
    nl2 = client.post("/nl/query", json={"trip_id": trip["id"], "question": "asdfghjkl random"}).json()
    assert nl2["intent"] == "unknown"

    # --- Slice 1: chat add/move + search endpoints ---
    # autocomplete over cached places
    hits = client.get("/places/search", params={"q": "red"}).json()
    assert isinstance(hits, list)

    # chat/add resolving to an EXISTING place (no live geocode) -> pending diff
    existing_name = client.get("/places").json()[0]["name"]
    add = client.post("/chat/add", json={"trip_id": trip["id"], "place_query": existing_name}).json()
    assert add["status"] == "pending"
    assert add["trigger"] == "chat_add"
    assert add["diff"]["added"], "add produces an 'added' diff entry"
    assert "day_index" in add["diff"]

    # confirm the add applies it (reuses the disruption confirm path)
    applied = client.post(f"/trips/{trip['id']}/changes/{add['id']}/confirm").json()
    assert applied["status"] == "applied"
