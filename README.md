# Tower Gacha — Dev Rough Draft

A roguelike tower-climbing gacha RPG. You are the manager. Heroes die permanently.

---

## Quick Start

# Terminal 1 — ComfyUI
cd C:\Users\liamh\ComfyUI 
venv\Scripts\activate 
python main.py

localhost:8188

# Terminal 2 — Backend
cd "C:\infinite gacha\tower-gacha\backend" 
venv\Scripts\activate 
uvicorn main:app --reload

backend

# Terminal 3 — Frontend
cd "C:\infinite gacha\tower-gacha\frontend" 
npm run dev

localhost:5173

---

## How to Play (Rough Draft Flow)

1. **Summon** tab → Pull heroes (costs 100g each, you start with 100g)
2. **Heroes** tab → Click heroes to select team (max 5), click "Set Team"
3. **Tower** tab → "Enter the Tower" → click "Advance to Floor X" each turn
4. Watch heroes fight deterministically. Deaths are permanent.
5. Every 10 floors you auto-return to base.
6. **Base** tab → "Rest All Heroes" to recover morale/stress between runs.

---

## Architecture

```
backend/
  main.py               # FastAPI app + CORS + static files
  database.py           # SQLite init + all table schemas
  services/
    gacha_service.py    # Weighted rarity pulls, stat generation, hidden aptitudes
    llm_service.py      # OpenAI calls: hero profiles, narration, events
    combat_service.py   # Deterministic combat simulation
    morale_service.py   # Morale/stress/trauma system
  routers/
    heroes.py           # Hero CRUD, team management
    gacha.py            # Pull endpoint
    tower.py            # Run start/advance/abandon, floor resolution
    base.py             # Base state, rest
    runs.py             # Run history, event log

frontend/src/
  App.jsx               # Tab layout, gold display
  api/client.js         # All API calls
  components/
    HeroCard.jsx        # Reusable hero display (stats, morale, HP bars, stars)
  pages/
    SummonPage.jsx      # Gacha pulls + odds display
    HeroesPage.jsx      # Hero roster + team management
    TowerPage.jsx       # Floor-by-floor progression + combat log
    BasePage.jsx        # Rest, materials, future upgrades
    LogPage.jsx         # Event history browser
```

---

## Known Rough Draft Limitations (things to build next)

- [ ] Event system (LLM-generated choices with consequences)
- [ ] Escort / survival mission types
- [ ] Ascension system (locked by floor, requires materials)
- [ ] Synthesis system (sacrifice heroes, morale consequences)
- [ ] Aptitude reveal system (hidden stats shown as heroes level)
- [ ] Pity system for gacha (guaranteed rate after N pulls)
- [ ] Skills / abilities in combat
- [ ] Status effects (burn, bleed, fear, stun)
- [ ] Enemy variety and scaling refinement
- [ ] Base upgrades that affect gameplay
- [ ] Legacy system (dead heroes leave passive bonuses)
- [ ] More gold income (floor rewards, base income)

---