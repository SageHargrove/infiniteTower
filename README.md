# Tower of Eternity

A roguelike tower-climbing gacha RPG. You are the manager. Heroes die permanently.

Summon heroes, send them up an endless Tower floor by floor, manage a home base
between climbs, and watch combat resolve as a deterministic simulation —
positioning, gear, class synergy, morale, and a hero's personality (their
"Ego") all matter, and a bad floor can permanently lose you a hero.

---

## Running It

**To just play the game:** run `app_launcher.py` (or the packaged desktop
build, if you've built one with PyInstaller — see `app_launcher.spec` /
`InfiniteGacha.spec`). It boots the backend, boots ComfyUI (for portrait
generation), and opens a desktop window pointed at the game — one step,
no manual terminals.

```
python app_launcher.py
```

The backend serves the frontend's built `dist/` directly, so if you've
changed any frontend code, rebuild it first:

```
cd frontend
npm run build
```

**For active frontend development** (live reload instead of rebuilding
every change), run the Vite dev server separately instead of relying on
the built `dist/`:

```
# Terminal 1 — Backend
cd backend
venv\Scripts\activate
python -m uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend (hot reload)
cd frontend
npm run dev
```

ComfyUI is only needed for generating new hero/enemy portraits — the game
runs fine without it, portraits just won't regenerate.

---

## How to Play

1. **Summon** → pull heroes with gold/gems.
2. **Heroes** → review hero stats, classes, aptitudes, Egos; set your team(s) (5 per team).
3. **Tower** → enter and advance floor by floor. Combat resolves automatically;
   deaths are permanent and leave a Legacy bonus for your roster.
4. **Base** → between climbs, assign heroes to Facilities (Forge, Infirmary,
   Market, etc.) and Base Upgrades, rest the roster, manage materials/equipment,
   and read the Hero Chatter log.
5. **Arena** → PvP against another player's snapshot team (see Known Gaps below).

---

## Architecture

```
backend/
  main.py                    # FastAPI app, CORS, serves frontend dist/ + static assets
  database.py                # SQLite schema, per-profile save files (saves/<profile>.db)
  services/                  # Game logic — combat, gacha, classes, egos, legacies,
                              # equipment, facilities, materials, level/ascension,
                              # skills, morale, events, LLM flavor text, portrait gen...
  routers/                   # API endpoints — heroes, gacha, tower, base, runs,
                              # equipment, relics, crafting, arena, profiles, chat
  static/portraits/          # Hero/enemy/boss art (git-ignored, locally generated)

frontend/src/
  App.jsx                    # Tab layout, forced onboarding tour, resource display
  api/client.js              # All API calls
  components/                # Reusable UI (HeroCard, CombatArena, tab tour overlay...)
  pages/                     # SummonPage, HeroesPage, TowerPage, BasePage, ArenaPage, LogPage

arena_server/                 # Separate small FastAPI service for Arena match
                               # resolution — not the main game backend.
```

---

## Known Gaps

Most of the original rough-draft TODO list (events, ascension, synthesis,
aptitude reveal, skills, legacy bonuses, escort/survival floors) is built.
What's still genuinely incomplete:

- **Gacha pity system** — pulls are pure weighted RNG, no guaranteed-rare-after-N-pulls floor yet.
- **Base Upgrades' described effects** — Barracks/Watchtower/Archive/Chapel/etc.
  can be purchased and leveled, but the effects their descriptions promise
  (bigger team size, floor-type reveal, faster trauma recovery...) aren't
  wired to any other system yet — it's a working currency sink, not yet a
  working mechanic.
- **Arena PvP** — the local backend only builds and submits a team snapshot;
  match resolution lives in the separate `arena_server/` and that loop isn't
  fully closed end-to-end yet (no live opponent matching/leaderboard in the main app).
- **Leaderboards / achievements** — not started.
- **Status effects** — fear/panic is fully simulated; burn/bleed/poison-style effects don't exist yet.
- **Inventory item use** — Bandages auto-apply pre-fight; Potions/Scrolls have
  no use path yet (no per-hero or shared item slot exists).
- **Enemy roster overhaul** — floor 1-10 has a themed family (Elites, a
  named miniboss, a named boss); floors 11-100 still use the older generic
  enemy pool, staged to be filled in one floor-range block at a time (see
  `PLAN_floor_workshop_enemies.md`).
