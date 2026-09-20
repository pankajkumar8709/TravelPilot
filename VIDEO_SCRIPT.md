# TravelPilot — Demo Video Script

**Length:** ~3 minutes (main) + a 60-second short cut at the bottom.
**Voice:** One narrator, plain friendly English. Short sentences. No jargon.
**Golden rule:** every scene below is a flow we have tested working end-to-end (Jaipur trip, chat explore/add, disruption diff). Record exactly this.

---

## Main script (~3 minutes)

| # | Time | What's on screen | Narration (say this) | On-screen text |
|---|------|------------------|----------------------|----------------|
| 1 | 0:00–0:20 | Landing page, hero photo, "Start planning" button | "Every trip planner can build you a plan. But what happens when things go wrong? A temple is closed. A flight is late. Your whole day falls apart. TravelPilot doesn't just make plans — it fixes them." | **Plan your trip** |
| 2 | 0:20–0:45 | Intake form. Type **Jaipur**, pick dates, budget, interests, press Generate | "Let's plan a trip to Jaipur. Pick your dates, your budget, what you like. Press generate. Behind the scenes, TravelPilot pulls real places from OpenStreetMap — real spots, real distances — and builds a day-by-day plan with actual timings. And this works for **any city** — we'll show you." | **Real places. Real timings. Any city.** |
| 3 | 0:45–1:15 | Scroll the day view: numbered cards, photos, travel-time labels. Then switch to Map | "Here is day one. Ten stops, in a sensible order — each card shows the time, the cost, and how long the walk is to the next place. The numbers follow your route. Switch to the map, and you see the same plan drawn as a line through the city. Same plan, two ways to see it." | **The journey is the interface** |
| 4 | 1:15–1:55 | Open the chat. Type: "show me more places near Hawa Mahal". Show the option cards | "Now the fun part. Talk to it. I ask for more places near Hawa Mahal — and it shows me real options nearby, with distances. I like the Wax Museum. One click to add it. It doesn't just change my plan silently — it shows me exactly what will change, and asks me to confirm. I confirm, and my plan is updated. That's how a plan should work." | **You talk. It plans. You approve.** |
| 5 | 1:55–2:30 | Press a "Simulate disruption" button. Diff card slides in: removed in red, added, with the reason. Point at the stability %. Confirm | "Here is the part no other planner does. Say it rains and one stop is cancelled. TravelPilot rebuilds **only the broken part** of your day — everything else stays exactly as it was. Look: it removed one stop, added a backup, and tells you why. 80 percent of your plan survived. You confirm, and you're back on track." | **Minimal repair. Not a rebuild.** |
| 6 | 2:30–2:50 | Budget card in the corner, language buttons on top | "It keeps track of your money — every ticket, every day. And it speaks your language: English, Hindi, Tamil, Bengali." | **Your budget. Your language.** |
| 7 | 2:50–3:00 | Back to the landing hero | "TravelPilot. Plans that fix themselves. Built on AWS — App Runner, RDS, and open map data — so it works even when the internet doesn't." | **TravelPilot — plans that repair themselves** |

---

## 60-second short version (Reels / Shorts)

| # | Time | What's on screen | Narration |
|---|------|------------------|-----------|
| 1 | 0:00–0:08 | Landing hero | "Trip planners build plans. This one repairs them. This is TravelPilot." |
| 2 | 0:08–0:20 | Intake → Generate → day view appears | "Pick any city — say Jaipur — and it builds a real plan with real places in seconds." |
| 3 | 0:20–0:32 | Chat: "show me more places near Hawa Mahal" → options → Add → Confirm | "Ask for more places. Like one? Add it. It shows you the change first — you approve it." |
| 4 | 0:32–0:48 | Disruption button → diff card → confirm | "And when a plan breaks, it repairs only the broken part. 80 percent of your day stays untouched." |
| 5 | 0:48–1:00 | Map view zoom out, logo | "Real places. Real timings. Plans that fix themselves. TravelPilot." |

---

## Recording notes

- **Do one clean run first.** Generate the Jaipur trip before recording so the city data is already cached — the second generation is instant.
- **Have a disruption story ready:** press "Simulate disruption" on the last stop of Day 1 for the cleanest minimal diff.
- **The chat moment needs live Groq** (`USE_MOCK_LLM=false` in `backend/.env`). If the demo machine is offline, the mock classifier still understands the same phrases — the screen looks identical.
- Keep the browser zoomed to ~125% so cards are readable on a laptop webcam or compressed video.
- Don't rush scene 5 — the diff card with the stability percentage is the whole point of the product. Let it sit on screen.

## The one line to end on (memorize)

> "Other planners give you a plan. When your plan breaks, TravelPilot gives you a repair."
