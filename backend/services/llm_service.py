import os
import json
import re
from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Fallback chain — tries each in order on rate limit
MODELS_BY_PRIORITY = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

RARITY_FLAVOR = {
    1: "a common peasant, laborer, or wanderer with humble origins",
    2: "a minor adventurer or soldier with some experience",
    3: "a seasoned fighter, skilled craftsman, or minor mage",
    4: "an elite warrior, veteran commander, or powerful spellcaster",
    5: "a legendary hero, archmage, or noble champion",
    6: "a near-mythic figure, ancient warrior, or transcendent being",
    7: "an impossibly rare entity — a demigod, an immortal, or a living legend",
}


class HeroProfile(BaseModel):
    name: str
    title: str
    backstory: str
    personality: str
    portrait_prompt: str


def _generate_with_fallback(prompt: str, max_tokens: int = 600, temperature: float = 0.9) -> str:
    """Try each Gemini model in order, falling back on rate limit errors."""
    last_error = None
    for model in MODELS_BY_PRIORITY:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            return response.text.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                print(f"[LLM] {model} rate limited, trying next...")
                last_error = e
                continue
            elif "API_KEY_INVALID" in err or "400" in err:
                print(f"[LLM] API key error: {e}")
                raise
            else:
                print(f"[LLM] {model} error: {e}")
                last_error = e
                continue
    raise Exception(f"All Gemini models exhausted. Last error: {last_error}")


def _clean_json(raw: str) -> str:
    """Strip markdown fences if model adds them."""
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return raw.strip()


def generate_hero_profile(birth_star: int, aptitudes: dict) -> HeroProfile:
    apt_names = {
        "apt_combat": "combat prowess",
        "apt_tactical": "tactical genius",
        "apt_survival": "survival instinct",
        "apt_mental": "mental fortitude",
        "apt_leadership": "leadership presence",
    }
    top_apt = max(aptitudes, key=aptitudes.get)
    top_apt_label = apt_names.get(top_apt, "unknown gift")

    prompt = f"""You are generating a hero for a dark fantasy roguelike tower-climbing game.

Hero rarity: {birth_star}★ — {RARITY_FLAVOR[birth_star]}
This hero has a notable hidden gift in: {top_apt_label} (do NOT state this directly — hint at it through personality and backstory)

Generate a hero profile. Be creative, grounded, and avoid clichés.
The world is dark, morally complex, and dangerous. Heroes are people, not archetypes.

Respond ONLY with valid JSON and nothing else — no markdown, no backticks, no preamble:
{{
  "name": "Full name (culturally varied, not generic fantasy)",
  "title": "Short epithet or nickname (e.g. 'The Twice-Burned', 'Ash of the North')",
  "backstory": "2-3 sentences. Specific, evocative, no tropes.",
  "personality": "1-2 sentences. How they act under pressure.",
  "portrait_prompt": "detailed anime portrait prompt, dark fantasy, specific appearance details, mood, lighting"
}}"""

    raw = _generate_with_fallback(prompt, max_tokens=600, temperature=0.9)
    data = json.loads(_clean_json(raw))
    return HeroProfile(**data)


def generate_combat_narration(combat_log: list, hero_names: list[str]) -> str:
    log_text = "\n".join([f"- {e}" for e in combat_log[-10:]])
    prompt = f"""You are narrating a battle in a dark fantasy roguelike game.
Heroes involved: {', '.join(hero_names)}

Combat events:
{log_text}

Write 2-4 sentences of vivid, grim narration. Focus on emotional weight, not just actions.
Be specific about names. Do not sugarcoat deaths or losses.
Respond with only the narration text, no preamble."""

    return _generate_with_fallback(prompt, max_tokens=200, temperature=0.8)


def generate_event_text(floor_number: int, event_type: str, context: str = "") -> dict:
    prompt = f"""You are generating a floor event for a dark fantasy roguelike.
Floor: {floor_number}, Event type: {event_type}
Context: {context or "Standard tower exploration."}

Respond ONLY with valid JSON and nothing else — no markdown, no backticks:
{{
  "title": "Short event name",
  "description": "2-3 sentence scene description. Grim, specific, atmospheric.",
  "choices": [
    {{"id": "a", "text": "Choice text", "hint": "Vague hint at consequence"}},
    {{"id": "b", "text": "Choice text", "hint": "Vague hint at consequence"}}
  ]
}}"""

    raw = _generate_with_fallback(prompt, max_tokens=400, temperature=0.85)
    return json.loads(_clean_json(raw))