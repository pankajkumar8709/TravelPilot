"""Disruption worker Lambda (Phase 0 placeholder -> Phase 7 real path).

Consumes SQS messages. Two message shapes:
  - Phase 0 test / EventBridge tick: {"probe": true}  -> logs and returns (proves the pipe).
  - Phase 7 real signal: {"trip_id":N,"day_index":D,"disrupted_place_id":P,"trigger":"weather"}
    -> POSTs to the backend /disruptions/inject so the SAME repair code runs as the
       manual button (plan: both triggers flow through the identical downstream path).

The scheduled EventBridge poll would enrich a raw weather/flight signal into that
shape; here we forward whatever the message carries.
"""
from __future__ import annotations

import json
import os
import urllib.request

API_BASE = os.environ.get("API_BASE_URL", "")


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def handler(event, _context):
    results = []
    for record in event.get("Records", [{"body": json.dumps(event)}]):
        try:
            msg = json.loads(record["body"])
        except (KeyError, json.JSONDecodeError):
            msg = {}

        if msg.get("probe") or not msg:
            print("[disruption-worker] probe/tick received — pipeline OK, nothing to repair.")
            results.append({"probe": True})
            continue

        if not API_BASE:
            print("[disruption-worker] API_BASE_URL unset; would repair:", msg)
            results.append({"skipped": "no API_BASE_URL", "msg": msg})
            continue

        try:
            out = _post("/disruptions/inject", {
                "trip_id": msg["trip_id"],
                "day_index": msg["day_index"],
                "disrupted_place_id": msg["disrupted_place_id"],
                "trigger": msg.get("trigger", "weather"),
                "reason": msg.get("reason", ""),
            })
            print("[disruption-worker] pending change created:", out.get("id"))
            results.append({"change_id": out.get("id")})
        except Exception as e:  # noqa: BLE001
            print("[disruption-worker] repair call failed:", e)
            results.append({"error": str(e)})

    return {"processed": len(results), "results": results}
