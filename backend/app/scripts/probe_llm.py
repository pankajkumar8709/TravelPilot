"""Probe — confirm the Groq LLM key works (replaces the Bedrock probe).

Does one tiny live chat completion against GROQ_MODEL so 'it works' is proven
before you flip USE_MOCK_LLM=false.

Usage:
  set GROQ_API_KEY=gsk_...        (or put it in backend/.env)
  python -m app.scripts.probe_llm
"""
from __future__ import annotations

from app.config import settings


def main() -> int:
    print(f"[probe_llm] provider=groq model={settings.groq_model}")
    if not settings.groq_api_key:
        print("[probe_llm] GROQ_API_KEY is not set. Get a free key at console.groq.com and put it in backend/.env")
        return 2
    try:
        import httpx

        r = httpx.post(
            f"{settings.groq_base_url}/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
            json={
                "model": settings.groq_model,
                "messages": [{"role": "user", "content": "Reply with the single word OK."}],
                "max_tokens": 10,
                "temperature": 0,
            },
            timeout=20,
        )
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]["content"].strip()
        print(f"[probe_llm] OK — Groq responded: {msg!r}")
        print("[probe_llm] You may set USE_MOCK_LLM=false now.")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"[probe_llm] FAILED: {e}")
        # On failure, list the models this key CAN use so we pick a live one.
        try:
            import httpx

            m = httpx.get(
                f"{settings.groq_base_url}/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                timeout=20,
            )
            m.raise_for_status()
            ids = [d["id"] for d in m.json().get("data", []) if d.get("active", True)]
            chat_ids = [i for i in ids if not any(x in i for x in ("whisper", "tts", "guard", "embed"))]
            print("[probe_llm] models your key CAN use (chat-capable):")
            for i in sorted(chat_ids):
                print(f"    {i}")
            print("[probe_llm] set GROQ_MODEL in backend/.env to one of the above.")
        except Exception as e2:  # noqa: BLE001
            print(f"[probe_llm] could not list models either: {e2}")
        print("  - the app still runs: it degrades to the mock automatically (degraded:true)")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
