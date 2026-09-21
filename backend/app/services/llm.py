"""LLM service — the LLM is the INTERFACE, not the authority (plan Phase 4/8).

Provider: Groq (OpenAI-compatible chat API). Bedrock was unavailable on this
AWS account, so the AI layer runs on Groq — a swap the architecture always
allowed, since the LLM only does two narrow jobs:

  Phase 4: map free-text interests + budget -> which interest tags/categories to
           prioritize and a budget split. The sequencing math stays deterministic
           in app/core/scheduler.py.
  Phase 8: intent classification + slot extraction ONLY — never reads/writes the DB.

Every call degrades to a deterministic mock if the provider is unreachable, the
key is missing, or USE_MOCK_LLM is set (so the whole app is demoable offline).
`degraded: true` is returned in that case instead of raising.
"""
from __future__ import annotations

import json
import re

from app.config import settings

KNOWN_TAGS = ["food", "culture", "outdoor", "shopping", "nightlife", "history"]

# Phase 8: fixed intent schema (intent name + required slots). The model outputs THIS, nothing else.
INTENTS = {
    "day_plan": ["day_reference"],        # "what should I do tomorrow morning?"
    "fit_check": ["activity_name"],       # "can I fit this into today?"
    "near_hotel": [],                     # "which activities are close to my hotel?"
    "what_if_cancel": ["booking_reference"],  # "what happens if this booking is cancelled?"
}


def _groq_chat(system: str, user: str, max_tokens: int, temperature: float) -> str:
    """One Groq chat completion via the OpenAI-compatible REST endpoint.
    Raises on any failure so callers fall back to the mock."""
    import httpx

    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY not set")
    r = httpx.post(
        f"{settings.groq_base_url}/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
        json={
            "model": settings.groq_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _mock_prioritize(interests_text: str, budget_total: float, days: int) -> dict:
    text = interests_text.lower()
    tags = [t for t in KNOWN_TAGS if t in text] or ["culture", "food", "outdoor"]
    weight = round(1.0 / len(tags), 3)
    return {
        "priority_tags": tags,
        "budget_split": {t: weight for t in tags},
        "daily_budget": round(budget_total / max(days, 1), 2) if budget_total else 0.0,
        "degraded": True,
    }


def prioritize_interests(interests_text: str, budget_total: float, days: int) -> dict:
    """Phase 4 — translate free-text interests/budget into structured filter params."""
    if settings.use_mock_llm:
        return _mock_prioritize(interests_text, budget_total, days)
    try:
        system = (
            "You map a traveler's interests to a fixed tag set and a budget split. "
            f"Allowed tags: {KNOWN_TAGS}. "
            'Respond with ONLY JSON: {"priority_tags":[...],"budget_split":{"tag":weight},'
            '"daily_budget":number}. No prose.'
        )
        user = f"Interests: {interests_text}\nTotal budget: {budget_total}\nDays: {days}"
        text = _groq_chat(system, user, max_tokens=400, temperature=0.2)
        data = json.loads(_extract_json(text))
        data["degraded"] = False
        # guard: never trust tags outside the known set
        data["priority_tags"] = [t for t in data.get("priority_tags", []) if t in KNOWN_TAGS] or ["culture"]
        if "daily_budget" not in data:
            data["daily_budget"] = round(budget_total / max(days, 1), 2) if budget_total else 0.0
        return data
    except Exception:
        return _mock_prioritize(interests_text, budget_total, days)


# Rich chat actions the user can express in free text (server-side routed).
CHAT_ACTIONS = {
    "add": ["place"],                    # "add IIT Delhi", "I want to go Nucleus Mall"
    "remove": ["place"],                 # "drop the fort", "remove Qutub Minar"
    "move": ["place", "to_day"],         # "move the museum to day 2"
    "shorten": ["place", "max_minutes"], # "only 2 hours at the fort"
    "nearby": ["reference"],             # "what's near my hotel / today's first stop"
    "explore": ["place"],                # "show me more places near India Gate"
    "resolve": ["place", "choice"],      # "add that one", "the second one", "Nucleus mall"
    "change_destination": ["destination"],  # "take me to Jaipur instead"
    "question": [],                      # anything else — answer inline
}


def classify_chat_action(message: str, day_count: int,
                         history: list[dict] | None = None,
                         trip_context: str = "") -> dict:
    """Extract a structured chat action + slots from free-form text.
    Groq when available (understands any phrasing / Hindi), else a keyword mock.
    `history` is the recent conversation [{role, content}] so follow-ups like
    'add that one' can be resolved against what was last offered.
    `trip_context` is a summary of the current trip (destination, days, budget,
    activity names) so the LLM understands what the user is referring to.
    Always returns {action, slots} with action in CHAT_ACTIONS."""
    if not settings.use_mock_llm and settings.groq_api_key:
        try:
            ctx_line = f"Current trip: {trip_context}. " if trip_context else ""
            system = (
                "You turn a traveler's message about their trip plan into ONE structured action. "
                f"Actions and slots: {json.dumps(CHAT_ACTIONS)}. "
                f"The trip has {day_count} days. "
                f"{ctx_line}"
                "Rules: 'add' = they want a new place (slot place = just the place name, no day words). "
                "If the request is GENERIC ('add a museum', 'add a park', 'some shopping'), keep that "
                "category word as the slot value verbatim (e.g. place='museum', place='park') — never "
                "the whole sentence, never padded with filler like 'a' or 'to the plan'. "
                "Strip trailing phrases like 'to the plan', 'to my trip', 'to the itinerary'. "
                "'move' needs to_day (1-based int). 'shorten' needs max_minutes (int). "
                "'nearby' = a quick informational what's-close-by question. "
                "'explore' = they want to DISCOVER more places near a landmark to potentially add "
                "(phrases like 'show me more places near X', 'what else is there around X', "
                "'other options near X', 'more places like X') — slot place = the landmark. "
                "'resolve' = they refer to a SPECIFIC place without a full sentence: follow-ups on "
                "previously offered options ('add that one', 'yes the second one' — slot choice = "
                "1-based int) or a bare place name ('Nucleus mall', 'IIIT Ranchi') — slot place = name. "
                "'change_destination' = they want the WHOLE trip moved to a different CITY "
                "(phrases like 'take me to X instead', 'change destination to X', 'replan in X') — "
                "slot destination = city name only. If X is clearly a place/venue, not a city, use 'add'. "
                "Use the conversation history to resolve references like 'that one' or 'it'. "
                "Use the trip context to understand which activities are in the plan and answer questions "
                "about them (e.g. 'what about the fort' refers to a fort in the trip's day plan). "
                "Messages may arrive in Hindi, Hinglish, or other languages — understand them and map "
                "to the same actions (e.g. 'मुझे एक संग्रहालय दिखाओ' = show me a museum -> 'add' with "
                "place='museum'; 'mujhe X day 2 pe move karo' = 'move'). "
                "Anything informational = 'question'. "
                'Respond with ONLY JSON: {"action":name,"slots":{...}}. No prose.'
            )
            transcript = "".join(
                f"{h.get('role', 'user')}: {str(h.get('content', ''))[:160]}\n"
                for h in (history or [])[-6:]
            )
            user = (f"Conversation so far:\n{transcript}\nCurrent message: {message}"
                    if transcript else message)
            text = _groq_chat(system, user, max_tokens=200, temperature=0.1)
            data = json.loads(_extract_json(text))
            if data.get("action") not in CHAT_ACTIONS:
                data = {"action": "question", "slots": {}}
            data.setdefault("slots", {})
            data["degraded"] = False
            return data
        except Exception:
            pass
    return _mock_chat_action(message, history=history)


def _mock_chat_action(message: str, history: list[dict] | None = None) -> dict:
    import re as _re
    q = message.lower().strip()
    day_m = _re.search(r"day\s*(\d+)", q)
    to_day = int(day_m.group(1)) if day_m else None

    # follow-up on previously offered options ('that one', 'second one', 'yes add it')
    if history:
        recent_bot = " ".join(str(h.get("content", "")) for h in history[-4:]
                              if h.get("role") == "bot").lower()
        if recent_bot and any(w in q for w in ("that one", "this one", "that place", "second one",
                                               "first one", "add it", "add that", "yes")):
            m2 = _re.search(r"(first|second|third|1st|2nd|3rd|\d)\s*(?:one|option)?", q)
            idx = None
            if m2:
                word = m2.group(1)
                idx = {"first": 1, "1st": 1, "second": 2, "2nd": 2,
                       "third": 3, "3rd": 3}.get(word) or (int(word) if word.isdigit() else None)
            return {"action": "resolve", "slots": {"choice": idx}, "degraded": True}

    def clean_place(text: str) -> str:
        text = _re.sub(r"\b(?:in|on|to)\s+day\s*\d+", "",
                       _re.sub(r"\bto (my |the )?(plan|trip|itinerary)\b", "", text))
        text = _re.sub(r"^(?:a|an|the|some|one)\s+", "", text)  # 'a museum' -> 'museum'
        return text.replace("  ", " ").strip()

    m = _re.match(r"(?:add|include|also see|let'?s see|visit)\s+(.+)", q)
    if m:
        return {"action": "add", "slots": {"place": clean_place(m.group(1)), "to_day": to_day}, "degraded": True}
    m = _re.match(r"i want to go(?:\s+to)?\s+(.+)", q)
    if m:
        return {"action": "add", "slots": {"place": clean_place(m.group(1)), "to_day": to_day}, "degraded": True}
    # bare place mention right after explore options ('Nucleus mall') -> resolve
    if history:
        recent = [str(h.get("content", "")) for h in history[-4:] if h.get("role") == "bot"]
        if recent and ("More places near" in recent[-1] or "options" in recent[-1].lower()):
            if 2 <= len(q.split()) <= 5 and not any(w in q for w in (
                    "plan", "day", "budget", "hotel", "near", "weather", "time")):
                return {"action": "resolve", "slots": {"place": q.title()}, "degraded": True}
    m = _re.match(r"(?:remove|drop|delete|skip|cancel)\s+(.+)", q)
    if m:
        return {"action": "remove", "slots": {"place": clean_place(m.group(1))}, "degraded": True}
    m = _re.match(r"move\s+(.+?)\s+to\s+day\s*(\d+)", q)
    if m:
        return {"action": "move", "slots": {"place": m.group(1).strip(), "to_day": int(m.group(2))}, "degraded": True}
    m = _re.search(r"(?:only|max|at most|no more than)\s+(\d+)\s*(?:hour|hr|min)", q)
    if m and ("hour" in q or "hr" in q):
        mins = int(m.group(1)) * 60
        name = _re.sub(r"(?:only|max|at most|no more than).*", "", q).replace("at the", "").replace("spend", "").strip()
        return {"action": "shorten", "slots": {"place": name, "max_minutes": mins}, "degraded": True}
    m = _re.search(r"(?:show|give|list|what)\s*(?:me\s*)?(?:some\s*)?(?:more\s*)?(?:other\s*)?(?:places|options|attractions|sights|spots|things)\b.*?(?:near|around|close to|by)\s+(.+?)(?:\?|$)", q) \
        or _re.search(r"(?:what|anything)\s+(?:else\s+)?(?:is\s+)?(?:there\s+)?(?:around|near|close to)\s+(.+?)(?:\?|$)", q) \
        or _re.match(r"(?:more|other|explore|discover)\s+(?:places|options|attractions|spots)\s*(?:near|around|close to)?\s*(.*)", q)
    if m:
        place = (m.group(1) or "").strip()
        place = _re.sub(r"\b(?:my\s+)?(hotel|current location|here)\b", "", place).strip()
        return {"action": "explore", "slots": {"place": place}, "degraded": True}
    m = _re.search(r"(?:take me to|change (?:the )?destination to|switch to|go to|replan? (?:my )?(?:trip )?in|what about (?:going to|planning for)|instead of)\s+(.+?)(?:\s+instead)?(?:\?|$)", q) \
        or _re.match(r"(?:plan|replan|rebuild)\s+(?:a\s+)?(?:trip|itinerary)\s+(?:for|in|to)\s+(.+?)(?:\?|$)", q)
    if m:
        dest = (m.group(1) or "").strip()
        dest = _re.sub(r"\b(?:instead|instead of this|this city|here)\b", "", dest).strip()
        if dest:
            return {"action": "change_destination", "slots": {"destination": dest.title()}, "degraded": True}
    if any(w in q for w in ["near my hotel", "around my hotel", "near the hotel", "close to my hotel"]):
        return {"action": "nearby", "slots": {"reference": "hotel"}, "degraded": True}
    if any(w in q for w in ["near", "close", "nearby", "around"]):
        # "more places near X" already matched explore above; plain "near X" is informational
        return {"action": "nearby", "slots": {"reference": "hotel" if "hotel" in q else "first"}, "degraded": True}
    return {"action": "question", "slots": {}, "degraded": True}


def classify_intent(question: str) -> dict:
    """Phase 8 — intent classification + slot extraction. Returns the fixed schema or unknown."""
    if settings.use_mock_llm:
        return _mock_intent(question)
    try:
        system = (
            "Classify the traveler's question into EXACTLY one intent and extract slots. "
            f"Intents and their slots: {json.dumps(INTENTS)}. "
            'Respond with ONLY JSON: {"intent":name,"slots":{...}}. '
            'If it does not match, use intent "unknown".'
        )
        text = _groq_chat(system, f"Question: {question}", max_tokens=300, temperature=0.1)
        data = json.loads(_extract_json(text))
        if data.get("intent") not in INTENTS:
            data = {"intent": "unknown", "slots": {}}
        data["degraded"] = False
        return data
    except Exception:
        return _mock_intent(question)


def _mock_intent(question: str) -> dict:
    q = question.lower()
    # Check SPECIFIC intents before the general day-reference catch-all, else a
    # fit/cancel question containing "today"/"tomorrow" mis-routes to day_plan.
    if "cancel" in q or "what happens if" in q:
        return {"intent": "what_if_cancel", "slots": {"booking_reference": ""}, "degraded": True}
    if "fit" in q or "can i fit" in q or "squeeze" in q:
        return {"intent": "fit_check", "slots": {"activity_name": ""}, "degraded": True}
    if "hotel" in q or "close" in q or "near" in q:
        return {"intent": "near_hotel", "slots": {}, "degraded": True}
    if any(w in q for w in ["tomorrow", "today", "morning", "afternoon", "evening", "do i"]):
        ref = "tomorrow" if "tomorrow" in q else "today"
        return {"intent": "day_plan", "slots": {"day_reference": ref}, "degraded": True}
    return {"intent": "unknown", "slots": {}, "degraded": True}


def phrase(result_summary: str, natural: bool = True, lang: str = "en") -> str:
    """Phase 8 — phrase a handler's structured result in natural language, in the
    requested language (multilingual NL support). English + mock => passthrough.
    On any failure, return the (English) summary rather than breaking the answer."""
    if lang == "en" and (settings.use_mock_llm or not natural):
        return result_summary
    if settings.use_mock_llm and lang == "en":
        return result_summary
    lang_names = {"en": "English", "hi": "Hindi", "ta": "Tamil", "bn": "Bengali"}
    target = lang_names.get(lang, "English")
    if settings.use_mock_llm:
        # no LLM available: can't translate, so return English but don't crash
        return result_summary
    try:
        system = (f"Rephrase the given trip fact as one friendly, concise sentence for a "
                  f"traveler, written in {target}. Plain text only, no JSON.")
        out = _groq_chat_text(system, result_summary, max_tokens=200, temperature=0.4)
        return out.strip() or result_summary
    except Exception:
        return result_summary


def _groq_chat_text(system: str, user: str, max_tokens: int, temperature: float) -> str:
    """Groq chat WITHOUT forced JSON — for free-text (translated) answers."""
    import httpx

    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY not set")
    r = httpx.post(
        f"{settings.groq_base_url}/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
        json={
            "model": settings.groq_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _extract_json(text: str) -> str:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else "{}"
