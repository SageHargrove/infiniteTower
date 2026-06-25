# Implementation Status — Survival Floor & Enemy Roster

Tracks the three things originally deferred for discussion. (1) and (2)
are resolved/built. (3) is in progress — floor 1-10's batch is built and
tested; the rest is staged for later, one floor-range block at a time.

---

## 1. Survival Floor (Boss Swarm Mechanic) — BUILT

A %5 miniboss floor has a 35% chance (`SWARM_SURVIVAL_CHANCE` in
`combat_service.py`) to roll a swarm-survival encounter instead of the
floor's usual single named miniboss — a random *alternative*, not a
replacement for every miniboss fight. Real combat, real death risk, same
as any other fight.

- 30-50 swarm units (`SURVIVAL_SWARM_COUNT_RANGE`) plus 1-2 genuine Elites
  mixed in (`SURVIVAL_SWARM_ELITE_COUNT_RANGE`), via
  `make_swarm_miniboss_encounter()`.
- Win condition: survive `SURVIVAL_TURN_LIMIT` (10) rounds with at least
  one hero alive — killing the whole swarm early still counts as a win,
  it's just not required. Wired via `run_combat`'s new `is_survival_swarm`
  / `turn_limit` params.
- Reward: same as a regular miniboss floor (see below) — no separate
  swarm-only bonus, since "it's a miniboss round" is already the bonus.
- Frontend: `CombatArena.jsx` shows a "Survive! Round X / N" badge instead
  of the normal enemy-count framing when `initial_state.is_survival_swarm`
  is set.
- Regular (non-%5/%10) floors are unaffected — their swarm archetype is
  still capped at 20 units, plain kill-them-all, exactly as before.

Also fixed along the way: **miniboss floors never had their own reward
bonus tier** — only Boss floors did. Added one (`_apply_combat_drops`,
`elif is_miniboss:`), roughly 40% of the Boss bonus. This is what makes
swarm-survival floors feel rewarded without a bespoke bonus path.

## 2. Workshop / Forge "Subset" Question — RESOLVED, scrapped

Tried Blacksmith/Tanner/Carpenter as three independent Forge specialists,
built it, then decided against it (needing high-star heroes in three
classes just to craft well). Reverted to Blacksmith-only — quality capped
by your single best (highest-tier) Blacksmith present, stacking same-tier
Blacksmiths adds a smaller bonus on top (`forge_smith_bonus` in
`class_service.py`). Closed unless a new reason to nest facilities comes up.

Still not covered: "more Blacksmiths = faster work" — crafting has no
time/cooldown component, so there's no "faster," only "better." Separate
ask if you want it.

---

## 3. Enemy Roster Overhaul — floor 1-10 built, rest staged

**Confirmed decisions from your notes:**
- Floor-range table (below) is likely final.
- Want Elite variants for *every* mob family eventually, in their own
  portrait subfolder, filtered by tier (normal/elite/miniboss/boss/raid_boss).
- Reusable mechanic library (not bespoke per-boss scripting) — confirmed.
- Floor 50 and 100 want something extra-special (halfway point / final
  floor) beyond the normal %10 boss treatment.
- **Art preserve-list — do not delete, ever, without asking first:**
  - Bosses: Lich King, Nightwing Devourer, Masked Horror (Undead Monarch
    is "okay but could be better"). Likely destined for a later, more
    humanoid "evil take on the 7-star" boss design direction.
  - Enemies: Bandit, Bone Warden, Shrouded Reaper, Rotting Ghoul.
  - If any don't end up fitting a family's archetype: ask before scrapping,
    or reuse their prompting as inspiration for a new entry. Confirmed
    untouched as of this pass (`portraits/enemies/*.png` and
    `portraits/bosses/boss_*.png` for all 8 names above, verified directly).

| Floors | Family | Status |
|---|---|---|
| 1-10 | Slimes, Goblins, Rats, Wolves | **Built** — 5 Elites, "Goblin King" miniboss, "The Warren Tyrant" boss |
| 11-20 | Kobolds, Skeletons, Orcs, Giant Spiders | Not started |
| 21-30 | Hobgoblins, Ghouls, Harpies, Lizardmen | Not started |
| 31-40 | Ogres, Trolls, Gargoyles, Wraiths | Not started |
| 41-50 | Minotaurs, Manticores, Wyverns, Elementals | Not started — floor 50 special boss lands here |
| 51-70 | Vampire Spawn, Chimeras, Golems, Naga | Not started |
| 71-90 | Hydras, Giants, Death Knights, Demon Lords | Not started |
| 91-100 | Dragons, Liches, Archdemons, Ancient Guardians | Not started — floor 100 special boss lands here |

**What's actually built for floor 1-10** (`services/enemy_families.py`,
`services/combat_service.py`):
- 5 new Elites: Acid Slime (self-regen), Goblin Warrior (cleave), Goblin
  Shaman (team-buff aura), Giant Rat Alpha (summons more Giant Rats),
  Wolf Alpha (enrages at low HP).
- Reusable ability library used by the above and available to any future
  family: `summon_add`, `team_buff_aura`, `self_regen` (joins the
  pre-existing `enrage`/`crushing_blow`/`last_stand`).
- Miniboss (floor 5): **Goblin King** — summons Goblins, cleaves.
- Boss (floor 10): **The Warren Tyrant** — summons Giant Rats, crushing
  blow, last stand.
- `_resolve_real_combat` → `run_multi_combat` looks up
  `enemy_families.get_miniboss_override`/`get_boss_override` by exact
  floor number; floors without an entry fall back to the old generic
  LLM-flavored boss naming — nothing breaks for ranges not built yet.
- Tier-specific portrait subfolders created: `portraits/enemies/elite/`,
  `miniboss/`, `boss/`, `raid_boss/` (empty, ready for art — falls back to
  a random existing boss portrait or the flat enemy-name lookup until
  dedicated art exists, same graceful fallback the game already had).

**Also fixed (pre-existing bug, not a new feature):** `run_multi_combat`
always built its enemy roster via the regular mob generator
(`make_enemies`), even on Boss/Miniboss floors — `make_boss()` was only
ever reachable via the every-20th-floor Raid Boss merge path. In practice
this meant every Boss floor that wasn't a multiple of 20 (10, 30, 50, 70,
90) and every Miniboss floor (5, 15, 25...) fought a regular mob
encounter instead of an actual named unique, and never got the Boss
reward bonus or correct frontend sprite sizing. Fixed — confirmed via
live test that floor 10 now fights "The Warren Tyrant" specifically and
gets the full Boss-tier gold bonus (3600 vs. the 600 it was getting before).

**Bosses built from the preserved art** (no Normal/Elite tier behind them
yet, just the boss slot itself):
- Floor 70 boss: **The Undead Monarch** (51-70 "Vampire Spawn" range).
- Floor 90 boss: **The Masked Horror** (71-90 "Death Knights" range).
- Floor 100 boss: randomly **The Lich King** or **The Nightwing Devourer**
  (91-100 "Liches"/"Dragons" range) — floor 100 already triggers the
  every-20th-floor Raid Boss merge and wanted something extra-special, so
  rather than picking one, it alternates between both.
- `make_boss`'s `family_override` now accepts an explicit `portrait_path`
  so a family can pin an exact existing piece of art (these 4 files,
  living under `static/portraits/bosses/`) instead of relying on the
  name-based tiered-folder lookup, which only checks the new
  `enemies/<tier>/` convention and wouldn't have found them there.

**Floor 11-20 family ("wave 2") was built, then pulled back out** — Kobold/
Skeleton/Orc Berserker/Giant Spider, Elites, miniboss Skeleton Champion
(needed a new `revive_ally` ability, still in combat_service.py's shared
ability library even though nothing uses it right now), boss Gorrath the
Bonebreaker. Built and tested working, but you hadn't finished reviewing/
clearing wave 1 (floor 1-10) yet, so per your call this got removed again —
going one wave at a time. The `revive_ally` ability and the floor-20
raid-merge `family_override`-forwarding fix (a real pre-existing bug, not
specific to wave 2) were left in place since they're harmless engine
infrastructure with no current callers, not wave-2 content themselves.
Floor 11-20 is back to the old generic enemy pool until wave 1 is signed
off and this gets revisited.

**Not done yet (next batches, by floor-range block):**
- Floor 11-99 Normal/Elite/Miniboss rosters — the 3 standalone bosses
  (70/90/100) are placeholders sitting on top of ranges that otherwise
  still use the old generic enemy pool.
- Floor 50's "extra special" treatment — no preserved art fit that range,
  still no design, flagged in `enemy_families.SPECIAL_BOSS_FLOORS` as a marker.
- Elite variants for the pre-existing enemies outside floor 1-10 (Troll,
  Ogre, Harpy, Dire Wolf, etc.) — only floor 1-10 got Elites so far, per
  "ship one block at a time, get it signed off" sequencing.

**Enemy/boss portrait library cleanup (this pass):** per your direct
confirmation, every enemy/boss portrait NOT on the preserve list was
deleted (backed up to a scratchpad temp folder first, not gone forever if
you change your mind on any of them — ask and I can restore). The 4
preserved enemy-tier portraits (Bandit, Bone Warden, Shrouded Reaper,
Rotting Ghoul) turned out to already be exact-name matches for existing
`ENEMY_TYPES` entries — they were never orphaned, just kept doing what
they were already doing. A new `enemies/normal/` folder now holds them
(and anything the background portrait-regeneration worker fills back in)
so the art library stays filterable by tier the way you wanted.

---

## 4. Inventory/Backpack Consumable System — separate ask, not yet started

Raised mid-conversation, not part of the original three items above:
heroes have no item slot, and Bandages are the only consumable currently
auto-applied (pre-fight, to the most-injured deployed heroes — see
`tower.py`'s `/floor/enter`). Potions and Scrolls exist as inventory items
but have no auto-use path at all. Needs its own design pass: shared
"backpack" vs. per-hero slot, and what "use at own discretion when low"
means precisely for a fight that resolves as one deterministic simulation
rather than a real-time player-controlled loop (most likely: extend the
turn loop itself to check HP each round and consume an available potion
from the shared pool, similar to how `self_regen`/abilities already work).
Scoped separately — not implemented in this pass.
