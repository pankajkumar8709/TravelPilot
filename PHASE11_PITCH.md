# Phase 11 — Pitch Prep

The technical work only lands if it's framed right in the time given. Memorize the
three sentences; rehearse the demo twice against the clock.

---

## The one-sentence problem
> "Every trip planner builds you a perfect itinerary — and then a flight delay or
> a rained-out afternoon turns it into a useless PDF you have to re-plan by hand."

## The positioning line (the sentence that separates you from the room)
> "TravelPilot doesn't just *generate* itineraries — it *repairs* them: when a
> disruption hits, it rebuilds only the affected part of your day and leaves the
> rest untouched."

Say this out loud, not off a slide. It's the whole differentiator in one breath:
**disruption-handling, not just generation.**

## The one technical flex (be ready to defend it)
> "We do **minimal-diff repair** instead of full regeneration — when one stop is
> disrupted we re-run the scheduler only on the affected time window and hold
> everything else fixed, then show a **plan-stability score**: the percentage of
> your original plan that survived. That's the exact metric current itinerary-repair
> research benchmarks on."

Follow-up defense if pressed:
- *"How do you know it's minimal?"* → We split the day into kept-prefix and
  affected-tail at the disrupted stop; only the tail is rescheduled. Provable —
  a day-1 disruption never touches day 2 (we test for exactly that).
- *"Why not just ask an LLM to redo it?"* → The LLM is the interface, not the
  authority. It classifies intent and prioritizes categories; the scheduling math
  is deterministic Python, so it never hallucinates a place or a time.

## Second technical flex (if they want architecture)
> "Reference data — places, hours, 1,560 real pairwise travel times — is fetched
> once from OpenStreetMap/OpenRouteService, landed raw in **S3**, and served from
> **RDS**. The app never calls an external data API at runtime, so a live API
> outage on demo day literally cannot touch us."

---

## Timed 3-minute demo script (rehearse TWICE)
| Time | Beat | What you say / do |
|------|------|-------------------|
| 0:00 | Problem | The one-sentence problem, above |
| 0:20 | Generate | Setup form → Paris, 3 days, €400, culture/history/outdoor → Generate. "Real place data, real travel times — not hardcoded." |
| 0:50 | Show the plan | Day tabs + map: numbered route, tag-colored markers, a food pin at a real meal-time location, the stay pin. |
| 1:20 | **THE MONEY SHOT** | Press 🌧 weather-disrupt. Diff view slides in: removed (red) / added (green) + plain-language reason. "It rebuilt *only* this slice." |
| 1:50 | Stability | Point at the plan-stability %. "87% of the plan survived — that's the research metric." Confirm → map re-renders. |
| 2:20 | NL + honesty | Ask "what should I do tomorrow morning?" → grounded answer. "The model never touches the database." |
| 2:40 | Close | Positioning line again + the S3/RDS reliability flex. "Deployed on AWS, and it can't be broken by a live outage." |

## Judging-criteria mapping (so nothing is left implicit)
- **Real problem** → disruption is a real, felt travel pain
- **Technical depth** → minimal-diff repair + stability score + deterministic engine
- **AWS usage** → App Runner + Amplify + RDS + S3 (+ EventBridge/SQS/Lambda pipeline)
- **Working demo** → the inject button proves the differentiator live, every time
- **Polish** → the diff view + map are the judge-facing screens, built last on a working system

## Rehearsal checklist
- [ ] Say the problem + positioning + flex sentences from memory (not reading)
- [ ] Time the full demo twice; trim if over 3 min
- [ ] Whoever says the flex can field one follow-up on it
- [ ] Demo trip pre-loaded in the tab before you present (no cold generate on stage)
