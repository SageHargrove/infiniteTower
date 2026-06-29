import json
import random
from database import db
from services.llm_service import _generate_with_fallback, _clean_json


def _tower_era(highest_floor: int) -> tuple[str, str]:
    """Buckets the save's overall progress into a fixed set of narrative eras —
    chatter should read as confused strangers early on, gradually settling into
    a lived-in understanding of the Tower as floors are cleared."""
    if highest_floor < 3:
        return "Awakening", (
            "This is VERY early on. Nobody understands the Tower or how they got "
            "here. The mood should be confusion, fear, and disorientation - lean "
            "into 'What is going on?' energy. They are strangers piecing together "
            "the absolute basics, not yet a found-family."
        )
    elif highest_floor < 15:
        return "Piecing It Together", (
            "The group has working theories about the Tower by now, though nothing "
            "is fully settled - expect debate, half-confident claims, and the "
            "occasional correction between heroes. Camaraderie is forming but "
            "confusion hasn't fully given way to confidence yet."
        )
    else:
        return "The Way Things Are", (
            "By now there's a settled, lived-in understanding of the Tower among "
            "the group - dark routine, inside jokes about Tower life, no more "
            "'what is this place' confusion. Long-timers talk like veterans."
        )


def _tenure_tag(hero_created_at: str, all_created_ats: list[str]) -> str:
    """'veteran' / 'newcomer' / '' (settled) based on this hero's percentile
    rank among currently-alive heroes' created_at — relative to the current
    roster, not a fixed date, so it stays meaningful no matter when a save is
    loaded. A hero pulled early is a 'veteran' of this world even in a
    late-game save where the Tower Era itself has long since settled."""
    if not hero_created_at or len(all_created_ats) < 3:
        return ""
    sorted_dates = sorted(all_created_ats)
    idx = sorted_dates.index(hero_created_at)
    pct = idx / max(1, len(sorted_dates) - 1)
    if pct <= 0.3:
        return "veteran"
    elif pct >= 0.7:
        return "newcomer"
    return ""


def generate_hero_chat() -> dict:
    """
    Selects heroes (preferably on a team or sharing synergy) and generates a chat log
    based on their personality, the current state of the base, and recent chats.
    """
    with db() as conn:
        heroes = conn.execute("SELECT id, name, personality, hero_class, level, ego_type, is_on_team, synergy_group, created_at FROM heroes WHERE is_alive = 1").fetchall()
        base_row = conn.execute("SELECT gold, highest_floor FROM base WHERE id = 1").fetchone()
        facilities = conn.execute("SELECT type FROM facilities").fetchall()
        recent_chats = conn.execute("SELECT message FROM hero_chat_logs ORDER BY created_at DESC LIMIT 2").fetchall()
        
    if not heroes:
        return {"status": "error", "message": "No alive heroes to chat."}
        
    gold = base_row["gold"] if base_row else 0
    highest_floor = base_row["highest_floor"] if base_row else 0
    unlocked_locations = ["The Lobby", "The Vault"] + [f["type"] for f in facilities]
    
    # Pick location
    location = random.choice(unlocked_locations)
    
    assigned_heroes = []
    with db() as conn:
        if location not in ["The Lobby", "The Vault"]:
            fac_row = conn.execute("SELECT id FROM facilities WHERE type = ?", (location,)).fetchone()
            if fac_row:
                assigned = conn.execute("SELECT h.id, h.name, h.personality, h.hero_class, h.level, h.ego_type, h.is_on_team, h.synergy_group FROM heroes h JOIN facility_assignments fa ON h.id = fa.hero_id WHERE fa.facility_id = ? AND h.is_alive = 1", (fac_row["id"],)).fetchall()
                if assigned:
                    assigned_heroes = [dict(r) for r in assigned]

    # Grouping logic: Try to pick heroes on the same team, or sharing synergy.
    grouped_heroes = {}
    heroes_dict_list = [dict(h) for h in heroes]
    for h in heroes_dict_list:
        if h["is_on_team"]:
            grouped_heroes.setdefault(f"Team {h['is_on_team']}", []).append(h)
        if h["synergy_group"]:
            grouped_heroes.setdefault(f"Synergy {h['synergy_group']}", []).append(h)
    
    valid_groups = [g for g in grouped_heroes.values() if len(g) >= 2]
    
    num_chatters = min(random.randint(2, 3), len(heroes))
    chatters = []
    
    if assigned_heroes:
        # Prioritize assigned heroes. Add a random wanderer if possible
        num_assigned = min(len(assigned_heroes), num_chatters)
        chatters = random.sample(assigned_heroes, num_assigned)
        if len(chatters) < num_chatters:
            wanderer_pool = [h for h in heroes_dict_list if h["id"] not in [c["id"] for c in chatters]]
            if wanderer_pool:
                chatters.append(random.choice(wanderer_pool))
    elif valid_groups and random.random() < 0.7:
        group = random.choice(valid_groups)
        chatters = random.sample(group, min(num_chatters, len(group)))
    else:
        chatters = random.sample(heroes_dict_list, num_chatters)
    
    era_name, era_instruction = _tower_era(highest_floor)
    all_created_ats = [h["created_at"] for h in heroes_dict_list]

    chatter_profiles = []
    for h in chatters:
        ego = f" (Ego: {h['ego_type']})" if h["ego_type"] else ""
        tenure = _tenure_tag(h["created_at"], all_created_ats)
        tenure_note = ""
        if tenure == "veteran":
            tenure_note = " [Has been in the Tower since early on - understands the basics, may explain things to others.]"
        elif tenure == "newcomer":
            tenure_note = " [Arrived recently - still getting their bearings, may ask questions others take for granted.]"
        chatter_profiles.append(f"- {h['name']}: Lvl {h['level']} {h['hero_class']}{ego}. Personality: {h['personality']}{tenure_note}")

    has_restaurant = any(f["type"] == "Restaurant" for f in facilities)
    has_chef = any(h["hero_class"] == "Chef" for h in heroes_dict_list)

    food_activity = "complaining about eating bland potatoes/rations"
    if has_restaurant and has_chef:
        food_activity = "praising the food or discussing the Chef's cooking"
    elif has_restaurant:
        food_activity = "complaining about the food being bland, but admitting it's better than rations"

    activities = [
        "playing a card game", "cleaning their weapons", food_activity, 
        "complaining about the smell", "bragging about a recent kill", 
        "nervously discussing the Tower", "enjoying a rare moment of peace",
        "arguing over a trivial matter", "sharing a rumor they heard"
    ]
    activity = random.choice(activities)
    
    recent_topics_prompt = ""
    if recent_chats:
        recent_topics_prompt = "CRITICAL INSTRUCTION: Do NOT repeat the general tropes or topics from these recent conversations (e.g. if they talked about silence/storms, DO NOT mention it):\n"
        for idx, rc in enumerate(recent_chats):
            try:
                msgs = json.loads(rc["message"])
                summary = " ".join([m["message"] for m in msgs])
                recent_topics_prompt += f"Recent Chat {idx+1}: {summary[:200]}...\n"
            except:
                pass
                
    prompt = f"""
You are writing a short, in-character chat log for a group of heroes hanging out in the base camp.
The current location they are at is: {location}.
They are currently {activity}.

Tower Era: {era_name}
{era_instruction}

Base State Context:
- Current Base Gold: {gold}
- Highest Tower Floor Cleared: {highest_floor}
- CRITICAL LORE: The heroes are climbing UP a massive Tower. Their goal is the TOP, not the "center" or "end of a labyrinth".
- CRITICAL LORE: The heroes are physically standing together in {location}, face to face. NEVER write lines implying radio, comms, static, signals, transmissions, or any kind of remote/long-distance communication — they are not separated and never hear from each other indirectly.

{recent_topics_prompt}

The heroes participating are:
{chr(10).join(chatter_profiles)}

Write a short, engaging 3-5 line conversation between them. Keep it realistic to their personalities and the current context. Make it feel alive and lived-in.
DO NOT use cliché tropes like "the silence is loud" or "quiet before the storm". Be highly creative.

Return ONLY a valid JSON array of message objects. Do not wrap in markdown tags like ```json.
Format:
[
  {{"speaker": "Hero Name", "message": "Their dialogue here"}},
  ...
]
"""
    try:
        response = _generate_with_fallback(prompt, max_tokens=300, temperature=0.9)
        chat_data = json.loads(_clean_json(response))
        
        if isinstance(chat_data, list) and len(chat_data) > 0:
            with db() as conn:
                participants_str = ", ".join([h["name"] for h in chatters])
                conn.execute(
                    "INSERT INTO hero_chat_logs (location, message, participants) VALUES (?, ?, ?)",
                    (location, json.dumps(chat_data), participants_str)
                )
                
                # Delete older logs keeping only the 5 most recent
                conn.execute("""
                    DELETE FROM hero_chat_logs 
                    WHERE id NOT IN (
                        SELECT id FROM hero_chat_logs 
                        ORDER BY created_at DESC 
                        LIMIT 5
                    )
                """)
            return {"status": "success", "chat": chat_data, "participants": participants_str, "location": location}
    except Exception as e:
        print(f"[Chat] Failed to generate chat: {e}")
        return {"status": "error", "message": str(e)}

import time
import threading

def chat_worker_loop():
    # Generates immediately on startup instead of only after the first
    # 300s sleep — a short play session never saw any chat at all before
    # this, since the loop used to sleep before ever calling
    # generate_hero_chat() even once. Still every 5 minutes after that.
    try:
        generate_hero_chat()
    except Exception as e:
        print(f'[Chat Worker] Error: {e}')
    while True:
        try:
            time.sleep(300)  # Generate new chat every 5 mins to save API quota
            generate_hero_chat()
        except Exception as e:
            print(f'[Chat Worker] Error: {e}')

def start_chat_worker():
    t = threading.Thread(target=chat_worker_loop, daemon=True)
    t.start()
