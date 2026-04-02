from fastapi import APIRouter, HTTPException
from database import db
from services.gacha_service import pull_rarity, generate_base_stats, generate_aptitudes, get_pull_cost
from services.llm_service import generate_hero_profile
from services.portrait_cache import claim_cached_portrait, queue_custom_portrait
from services.class_service import assign_class, can_pilot
from services.level_service import recalculate_hero_level
from pydantic import BaseModel

router = APIRouter()

class PullRequest(BaseModel):
    count: int = 1

@router.post("/pull")
def pull_heroes(req: PullRequest):
    if req.count < 1 or req.count > 10:
        raise HTTPException(status_code=400, detail="Pull 1-10 heroes at a time")

    cost = get_pull_cost() * req.count

    with db() as conn:
        base_row = conn.execute("SELECT gold FROM base WHERE id = 1").fetchone()
        if not base_row or base_row["gold"] < cost:
            raise HTTPException(status_code=400, detail=f"Not enough gold. Need {cost}g.")
        conn.execute("UPDATE base SET gold = gold - ? WHERE id = 1", (cost,))

    results = []
    for _ in range(req.count):
        birth_star = pull_rarity()
        stats = generate_base_stats(birth_star)
        aptitudes = generate_aptitudes(birth_star)
        hero_class = assign_class(birth_star)
        pilot = 1 if can_pilot(hero_class) else 0

        # LLM text generation with fallback
        try:
            profile = generate_hero_profile(birth_star, aptitudes)
        except Exception as e:
            print(f"LLM profile failed: {e}")
            class FallbackProfile:
                name = f"Unknown {birth_star}★"
                title = "The Nameless"
                backstory = "Their past is unknown, swallowed by the tower."
                personality = "Watchful and silent."
                portrait_prompt = f"dark fantasy anime warrior portrait, {birth_star} star rarity"
            profile = FallbackProfile()

        # Claim cached portrait instantly
        portrait_path = claim_cached_portrait(birth_star)

        with db() as conn:
            cursor = conn.execute("""
                INSERT INTO heroes (
                    name, title, backstory, personality, portrait_path,
                    birth_star, hero_class, can_pilot, level,
                    hp, max_hp, attack, defense, speed,
                    apt_combat, apt_tactical, apt_survival, apt_mental, apt_leadership
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                profile.name, profile.title, profile.backstory,
                profile.personality, portrait_path,
                birth_star, hero_class, pilot, 1,
                stats["hp"], stats["max_hp"], stats["attack"],
                stats["defense"], stats["speed"],
                aptitudes["apt_combat"], aptitudes["apt_tactical"],
                aptitudes["apt_survival"], aptitudes["apt_mental"],
                aptitudes["apt_leadership"],
            ))
            hero_id = cursor.lastrowid
            hero = conn.execute("SELECT * FROM heroes WHERE id = ?", (hero_id,)).fetchone()
            results.append(dict(hero))

        # Queue custom portrait in background
        queue_custom_portrait(hero_id, profile.portrait_prompt, profile.name)

    return {"pulled": results, "cost": cost}

@router.get("/odds")
def get_odds():
    from services.gacha_service import RARITY_WEIGHTS, TOTAL_WEIGHT
    return {
        str(star): {
            "weight": w,
            "percent": round(w / TOTAL_WEIGHT * 100, 4)
        }
        for star, w in RARITY_WEIGHTS.items()
    }

@router.get("/cache-status")
def cache_status():
    from services.portrait_cache import get_cache_counts
    counts = get_cache_counts()
    return {"available": counts, "total": sum(counts.values())}

@router.get("/class-info")
def class_info():
    from services.class_service import CLASS_ICONS, CLASS_DESCRIPTIONS
    return {"icons": CLASS_ICONS, "descriptions": CLASS_DESCRIPTIONS}