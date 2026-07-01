"""
Event Service — Deterministic floor events with LLM narration.

Events are selected from a template pool. The backend determines ALL mechanical
outcomes. The LLM only generates narrative text and choice flavor.
"""
import random

EVENT_TEMPLATES = [
    {
        "id": "abandoned_camp",
        "theme": "The team discovers an abandoned campsite. The fire is long cold, but deep claw marks scar the surrounding stone. A heavy iron lockbox sits half-buried in the ash, chained to the frozen corpse of a previous climber.",
        "choices": [
            {"id": "search", "label": "Break the chains and loot the box", "hint": "Whatever killed them is still close",
             "outcomes": {"gold": (50, 150), "hlt_pct": (-0.10, -0.05), "stress": (10, 25), "trigger_combat": True}},
            {"id": "ignore", "label": "Leave it and move silently", "hint": "Safe, but yields nothing",
             "outcomes": {"gold": (0, 0), "hlt_pct": (0, 0), "stress": (-5, 0)}},
        ]
    },
    {
        "id": "wounded_stranger",
        "theme": "A horrific coughing echoes from the shadows. A wounded climber is propped against the wall, his legs crushed beneath fallen rubble. His eyes are wild with fear, and he clutches a glowing bag of supplies.",
        "choices": [
            {"id": "help", "label": "Spend hours freeing him", "hint": "Morally right, but exhausting",
             "outcomes": {"gold": (10, 30), "hlt_pct": (-0.05, -0.05), "morale": (10, 20), "stress": (5, 10)}},
            {"id": "ignore", "label": "Walk past his pleas", "hint": "Preserve your strength",
             "outcomes": {"gold": (0, 0), "morale": (-15, -10), "stress": (10, 15)}},
            {"id": "loot", "label": "Kill him and take the supplies", "hint": "Pragmatic cruelty — it changes you",
             "outcomes": {"gold": (80, 200), "morale": (-30, -20), "trauma": (5, 15), "stress": (0, 5),
                          "trait": {"id": "cold_blooded", "name": "Cold-Blooded", "type": "passive",
                                    "desc": "+3% crit chance, permanently — that first kill for gain was never the last time it got easier.",
                                    "effect": {"crit_pct": 0.03}}}},
        ]
    },
    {
        "id": "blood_fountain",
        "theme": "A grand, gothic fountain stands in the center of the hall, but it runs thick with fresh blood instead of water. Whispers echo from the red basin, promising vitality to those who drink.",
        "choices": [
            {"id": "drink", "label": "Drink from the bloody basin", "hint": "Gain strength permanently, invite madness",
             "outcomes": {"hlt_pct": (0.15, 0.30), "stress": (15, 30), "trauma": (2, 5),
                          "trait": {"id": "blood_kissed", "name": "Blood-Kissed", "type": "passive",
                                    "desc": "+4% Health, permanently — the fountain's gift never fully fades.",
                                    "effect": {"hlt_pct": 0.04}}}},
            {"id": "leave", "label": "Refuse the unnatural gift", "hint": "Avert your eyes and pass",
             "outcomes": {"stress": (0, 5), "morale": (-5, 0)}},
        ]
    },
    {
        "id": "mysterious_altar",
        "theme": "An ancient obsidian altar dominates the room, piled high with decaying offerings. An oppressive, divine weight presses down on your minds, demanding tribute.",
        "choices": [
            {"id": "pray", "label": "Kneel and offer a prayer of submission", "hint": "The tower demands respect",
             "outcomes": {"morale": (15, 30), "trauma": (-8, -3), "stress": (-15, -5)}},
            {"id": "destroy", "label": "Defile the altar and smash the idols", "hint": "Defy what watches you — it answers",
             "outcomes": {"gold": (100, 250), "morale": (-20, -10), "trauma": (5, 10), "hlt_pct": (-0.15, -0.05), "trigger_combat": True}},
        ]
    },
    {
        "id": "echoing_voices",
        "theme": "As you walk through a narrow cavern, the heroes hear the distinct voices of their dead loved ones calling out from the abyss below, begging them to jump.",
        "choices": [
            {"id": "listen", "label": "Stop and listen to the voices", "hint": "A dangerous indulgence — something climbs up",
             "outcomes": {"morale": (-20, 10), "trauma": (5, 15), "stress": (10, 25), "trigger_combat": True}},
            {"id": "ignore", "label": "Cover your ears and march forward", "hint": "Steel your mind",
             "outcomes": {"stress": (5, 15)}},
        ]
    },
    {
        "id": "mad_merchant",
        "theme": "A grotesque, multi-armed creature wearing the tattered robes of a merchant sits amidst a pile of gleaming artifacts. It doesn't want gold; it wants your sanity in exchange for its wares.",
        "choices": [
            {"id": "trade", "label": "Gaze into its eyes and trade", "hint": "Suffer mental damage for wealth and insight",
             "outcomes": {"gold": (150, 300), "stress": (25, 40), "trauma": (3, 8),
                          "trait": {"id": "soul_bartered", "name": "Soul-Bartered", "type": "passive",
                                    "desc": "+4% Intelligence, permanently — you understand something now that you didn't before, and can't un-know it.",
                                    "effect": {"int_pct": 0.04}}}},
            {"id": "refuse", "label": "Back away slowly", "hint": "Leave empty-handed but sane",
             "outcomes": {"stress": (0, 0)}},
        ]
    },
    {
        "id": "trapped_room",
        "theme": "The stone floor suddenly drops an inch with a sickening 'click'. Iron bars slam down over the doors, and the ceiling begins slowly lowering, covered in rusted spikes.",
        "choices": [
            {"id": "rush", "label": "Dive desperately for the gap", "hint": "Agility over caution — it sharpens your instincts",
             "outcomes": {"hlt_pct": (-0.25, -0.10), "stress": (15, 25),
                          "trait": {"id": "near_miss_reflexes", "name": "Near-Miss Reflexes", "type": "passive",
                                    "desc": "+3% dodge chance, permanently — your body remembers how close that was.",
                                    "effect": {"dodge_pct": 0.03}}}},
            {"id": "careful", "label": "Jam the mechanism with weapons", "hint": "Sacrifice gear for safety",
             "outcomes": {"hlt_pct": (-0.05, 0), "gold": (-50, -20), "stress": (5, 15)}},
        ]
    },
    {
        "id": "fallen_hero_remains",
        "theme": "You find the mangled remains of a previous expedition's champion. They died clutching a locket, their legendary equipment scattered in the dust.",
        "choices": [
            {"id": "honor", "label": "Bury them and pay respects", "hint": "Honor the fallen",
             "outcomes": {"morale": (15, 25), "trauma": (-5, -2), "stress": (-10, -5), "item": "Legendary Locket",
                          "trait": {"id": "honored_by_the_fallen", "name": "Honored by the Fallen", "type": "passive",
                                    "desc": "+3% Health, permanently — something of their resolve stayed with you.",
                                    "effect": {"hlt_pct": 0.03}}}},
            {"id": "salvage", "label": "Strip the corpse of everything valuable", "hint": "The dead need nothing",
             "outcomes": {"gold": (80, 180), "morale": (-15, -5), "trauma": (4, 8), "item": "Legendary Locket"}},
        ]
    },
    {
        "id": "tragic_sacrifice",
        "theme": "A monolithic gate blocks the path, sealed by blood magic. The whispers of the tower are clear: 'A life for passage. Only blood opens the way.' The gate requires a living sacrifice.",
        "choices": [
            {"id": "sacrifice", "label": "Offer one of your own to the gate", "hint": "A random hero dies permanently, but the rest survive untouched.",
             "outcomes": {"sacrifice_hero": True, "morale": (-40, -30), "trauma": (20, 30), "stress": (20, 30)}},
            {"id": "resist", "label": "Refuse and force the gate open with sheer will", "hint": "Everyone suffers massive damage, but survives changed",
             "outcomes": {"hlt_pct": (-0.80, -0.60), "stress": (40, 60), "trauma": (10, 20), "morale": (-20, -10),
                          "trait": {"id": "iron_willed", "name": "Iron-Willed", "type": "passive",
                                    "desc": "+2% all stats, permanently — you forced a god's gate open with nothing but spite.",
                                    "effect": {"all_pct": 0.02}}}},
        ]
    },
]


def select_event(floor_number: int, zone_theme: str = None) -> dict:
    template = random.choice(EVENT_TEMPLATES)
    return {
        "template_id": template["id"],
        "theme": template["theme"],
        "choices": [
            {"id": c["id"], "label": c["label"], "hint": c["hint"]}
            for c in template["choices"]
        ],
    }


def get_event_theme(template_id: str) -> str:
    """The actual scenario text for this template — used for the resolution
    narrative instead of the request body's stale zone-level theme, which
    was the original 'the narration and choices describe two different
    encounters' bug (zone theme vs. the specific event rolled)."""
    template = next((t for t in EVENT_TEMPLATES if t["id"] == template_id), None)
    return template["theme"] if template else "An event occurred."


def resolve_event_choice(template_id: str, choice_id: str, heroes: list[dict]) -> dict:
    template = next((t for t in EVENT_TEMPLATES if t["id"] == template_id), None)
    if not template:
        return {"error": "Unknown event template"}
    choice = next((c for c in template["choices"] if c["id"] == choice_id), None)
    if not choice:
        return {"error": "Unknown choice"}
    outcomes = choice["outcomes"]
    resolved = {}
    for key, val in outcomes.items():
        if isinstance(val, tuple):
            lo, hi = val
            if isinstance(lo, float):
                resolved[key] = round(random.uniform(lo, hi), 3)
            else:
                resolved[key] = random.randint(min(lo, hi), max(lo, hi))
        else:
            resolved[key] = val
    return {
        "template_id": template_id,
        "choice_id": choice_id,
        "choice_label": choice["label"],
        "effects": resolved,
    }
