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
2. **Heroes** → review hero stats, classes, aptitudes, Egos, skills (5-tier
   class-specific active/passive kits), traits, and weapon/armor affinity;
   set your team(s) (5 per team).
3. **Tower** → enter and advance floor by floor — combat, event (narrative
   choice, sometimes turning into a real fight), explore, escort, survival,
   and other floor types. Combat resolves automatically; deaths are
   permanent and leave a Legacy bonus for your roster. Floor type/blurb
   stays hidden (?) until you've actually visited it once.
4. **Base** → between climbs, assign heroes to Facilities (Forge, Infirmary,
   Market, etc.) and Base Upgrades, rest the roster, manage materials/equipment
   (including weapon types — Sword/Spear/Staff/Bow/Dagger — and armor types —
   Robe/Light/Brigandine/Heavy — each with class-restricted equip and their
   own stat flavor), and read the Hero Chatter log / Lore Journal.
5. **Arena** → PvP against another player's snapshot team (see Known Gaps below).
6. **Achievements** → singleplayer milestones (floors, summons, battles, gear,
   wealth) plus a few PvP-rating ones that just sit locked until Arena is
   live. Rewards are gems, and for the hardest ones, a Summon Ticket — a
   consumable (Items tab) that guarantees a 4★+/5★+/6★+/7★+ hero pull.

---

## Architecture

```
backend/
  main.py                    # FastAPI app, CORS, serves frontend dist/ + static assets
  database.py                # SQLite schema, per-profile save files (saves/<profile>.db)
  services/                  # Game logic — combat, gacha, classes (3-way schema:
                              # core combat / support-combat / utility-profession,
                              # plus weapon & armor type affinity), egos, legacies,
                              # equipment, facilities, materials, level/ascension,
                              # skills (full 5-tier kits per class lineage), morale,
                              # events, LLM flavor text, portrait gen...
  routers/                   # API endpoints — heroes, gacha, tower, base, runs,
                              # equipment, relics, crafting, arena, profiles, chat
  static/portraits/          # Hero/enemy/boss art (git-ignored, locally generated)

frontend/src/
  App.jsx                    # Tab layout, forced onboarding tour, resource display
  api/client.js              # All API calls
  components/                # Reusable UI (HeroCard, CombatArena, tab tour overlay...)
  pages/                     # SummonPage, HeroesPage, TowerPage, BasePage, ArenaPage,
                              # AchievementsPage, InventoryPage, LogPage

arena_server/                 # Separate small FastAPI service for Arena match
                               # resolution — not the main game backend.
```

---

## Known Gaps

- **Arena PvP** — fully wired end-to-end (ArenaPage.jsx -> arenaServerClient.js
  -> arena_server/, with the main backend just exporting a team snapshot via
  /arena/team/{id}/snapshot). Matchmaking and leaderboards are implemented in
  arena_server/. Not currently running as a live service — the game's combat/
  skill/equipment systems are still changing too often for a hosted PvP server
  to stay balanced — but there's no missing infrastructure, just a deliberate
  choice not to launch it yet. **One real gap:** arena_server has no way to
  report match results back to a player's local profile/save, so the
  Achievements system's 3 PvP-rating achievements (Arena Debut/Gladiator/
  Champion, gated on `base.arena_wins`) will stay at 0 progress until that
  result-reporting round trip is built — they're visible in the list either
  way, per design, just locked.
- **Achievements** — implemented (`services/achievement_service.py`,
  `routers/achievements.py`, AchievementsPage.jsx): 34 achievements across
  Tower/Summoning/Roster/Combat/Economy/Equipment/Arena, computed live off
  existing save state plus 4 new counters on `base`
  (total_summons/total_battles_won/arena_wins/arena_losses). Rewards are
  mostly gems; the hardest ones grant a Summon Ticket.
- **Summon Tickets** — implemented (`/gacha/use-ticket`, item_type
  `summon_ticket` in `inventory`): a guaranteed-minimum-star single hero
  pull (4★/5★/6★/7★ tiers), reusing the same hero-creation pipeline as a
  normal gacha pull. Currently only obtainable as Achievement rewards —
  there's no separate event-drop or shop-purchase path for them yet.
- **Enemy roster overhaul art** — waves of floors is implemented; enemy art needs polish
