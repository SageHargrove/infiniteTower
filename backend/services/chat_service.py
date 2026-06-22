import json
import random
from database import db
from services.llm_service import _generate_with_fallback, _clean_json

def generate_hero_chat() -> dict:
    """
    Selects heroes (preferably on a team or sharing synergy) and generates a chat log 
    based on their personality, the current state of the base, and recent chats.
    """
    with db() as conn:
        heroes = conn.execute("SELECT id, name, personality, hero_class, level, ego_type, is_on_team, synergy_group FROM heroes WHERE is_alive = 1").fetchall()
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
    
    chatter_profiles = []
    for h in chatters:
        ego = f" (Ego: {h['ego_type']})" if h["ego_type"] else ""
        chatter_profiles.append(f"- {h['name']}: Lvl {h['level']} {h['hero_class']}{ego}. Personality: {h['personality']}")
        
    activities = [
        "playing a card game", "cleaning their weapons", "bickering over food", 
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

Base State Context:
- Current Base Gold: {gold}
- Highest Tower Floor Cleared: {highest_floor}

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
    while True:
        try:
            time.sleep(300)  # Generate new chat every 5 mins to save API quota
            generate_hero_chat()
        except Exception as e:
            print(f'[Chat Worker] Error: {e}')

def start_chat_worker():
    t = threading.Thread(target=chat_worker_loop, daemon=True)
    t.start()
