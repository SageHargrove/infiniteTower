# Implementation Plan (Draft — Nothing Below Is Built Yet)

Covers the three things explicitly deferred for discussion: the survival
floor mechanic, the Workshop/Forge "subset" question, and the full
enemy-roster overhaul. Existing content (all 38 current enemies, the
current Forge/Workshop facilities) stays untouched no matter which
direction we pick — this is additive.

---

## 1. Survival Floor (Boss Swarm Mechanic)

**The ask:** a manga-style "overwhelming swarm" boss floor — can't kill
them all, win by surviving instead.

**What's already true in the code (researched, not guessed):**
- Combat's win condition today is strictly "all enemies dead" or "all
  heroes dead" — no other exit exists (`combat_service.py`'s turn loop).
- There's already a hard `max_rounds = 30` safety cap on every fight, and
  a `"survival"` floor *type* already exists in `floor_templates.py` —
  but it currently just spawns 6-8 enemies and still plays by the normal
  kill-everyone win condition. It's a survival floor in name only right now.
- The floor-type system already does `floor % 10 == 0` → boss,
  `floor % 5 == 0` (not %10) → miniboss. A new floor type slots in cleanly.
- Enemy group sizing already has a "swarm" archetype (very weak
  individually — 0.3-0.5x stats — but spawns in bulk, up to ~20 per fight
  currently). Spawning even more (tested architecturally fine up to
  ~100) is not a performance wall — Python/JSON overhead at that count is
  trivial. 1.5k like the manga obviously isn't happening, but 30-60
  visually-implied-as-"countless" is realistic.

**Proposed shape:**
- New `turn_limit` parameter on `run_combat`. Win condition becomes:
  `(all enemies dead) OR (survived turn_limit rounds with ≥1 hero alive)`.
- Reuse the swarm archetype almost as-is for the bulk of the spawn —
  individually trivial, dangerous in volume. Maybe layer 1-2 "Elite"
  units into the swarm as the actual threat that can drop a hero, while
  the swarm itself is mostly chip damage / forces hard choices.
- Frontend needs a round counter ("Survive 4 more rounds!") instead of
  the normal "X enemies remaining" framing.

**Decided:** miniboss floors (`%5==0`, not `%10`) only — not full boss
floors. Confirmed good idea, just scoped smaller than a true boss
encounter.

**Still open:**
- Reward shape — flat completion bonus, or scaled by rounds survived /
  damage dealt before the timer runs out?
- Should heroes face real death risk here like normal combat, or is this
  meant to feel like a softer set-piece (e.g. trauma/death disabled,
  pure spectacle)?

---

## 2. Workshop / Forge "Subset" Question — RESOLVED, scrapped

We tried the Tanner/Carpenter-as-independent-Forge-specialists design
(each owning a slot — weapon/armor/accessory — solo-capable, with a
teamwork bonus for stacking lines) and built it end-to-end. You decided
against it: it meant needing high-star/talented heroes in three separate
classes just to craft well, versus the simpler "just invest in good
Blacksmiths" model. **Reverted.** Forge crafting is Blacksmith-only
again, but with the nuance you wanted: quality is capped by your single
*best* (highest-evolution-tier) Blacksmith present, not an averaged-down
group score, and stacking more Blacksmiths of that same tier adds a
smaller bonus on top (`forge_smith_bonus` in `class_service.py`). A pile
of low-tier smiths can't out-craft one well-evolved one.

Given that, the nested "Workshop contains Forge as a sub-station"
structural question doesn't have an active driver anymore either — it
was motivated by wanting Tanner/Carpenter to feel like their own thing,
and that whole direction is gone. Treat this section as closed unless a
genuinely new reason to nest facilities comes up later (e.g. a real
second crafting station with its own assignment slots).

One open item from the original ask that's *not* covered yet: "more
Blacksmiths = faster work." There's no time/cooldown component to
crafting right now — every craft is a single instant action. The
quality-ceiling model above covers "better," not "faster." If you want
crafting to actually take time (a queue, a cooldown reduced by crew
size), that's a separate, bigger mechanic — flag it if you want it
scoped.

---

## 3. Enemy Roster Overhaul

**Current state (confirmed from the actual file):** 38 enemies total,
spread across 4 unlock-floor tiers (beginner@1, intermediate@15,
advanced@40, legendary@70). Not zone-grouped, not Normal/Elite/Miniboss/Boss
tiered. The only existing "boss" framing is the every-20-floors Raid Boss
(all teams merge into one fight) — unrelated to a per-family tier system.
**Nothing here gets deleted** — every existing enemy folds into the new
structure as that family's "Normal" tier for its floor range.

**Your proposed roster, restated as floor ranges:**

| Floors | Family |
|---|---|
| 1-10 | Slimes, Goblins, Rats, Wolves |
| 11-20 | Kobolds, Skeletons, Orcs, Giant Spiders |
| 21-30 | Hobgoblins, Ghouls, Harpies, Lizardmen |
| 31-40 | Ogres, Trolls, Gargoyles, Wraiths |
| 41-50 | Minotaurs, Manticores, Wyverns, Elementals |
| 51-70 | Vampire Spawn, Chimeras, Golems, Naga |
| 71-90 | Hydras, Giants, Death Knights, Demon Lords |
| 91-100 | Dragons, Liches, Archdemons, Ancient Guardians |

Plus your elite-variant examples (Goblin Warrior, Goblin Shaman, Orc
Berserker, Skeleton Knight, Skeleton Mage, Dire Wolf Alpha, Elite Kobold
Scout, Ogre Chieftain, Troll Champion), and the 4-tier encounter model
from the Discord notes:

- **Normal** — standard enemy, what's already in `ENEMY_TYPES`.
- **Elite** — same species, better stats, one extra ability. The
  "elite" archetype already exists mechanically (1.5x stat multiplier) —
  just needs the ability hook added per family.
- **Mini-Boss** — named unique variant, every 5th floor (not %10).
  Needs a real mechanic, not just stats: "Goblin King summons goblins,"
  "Skeleton Champion revives the fallen," etc. This is new combat logic
  per family, not just a bigger stat block.
- **Boss** — every 10th floor. Multiple abilities, phases, unique art,
  special rewards. Biggest lift per-entry.

**Migration plan:**
1. Re-tag the 38 existing enemies into the floor-range table above as
   each family's Normal tier (mostly a relabeling — floor-range tiers
   replace the current beginner/intermediate/advanced/legendary labels,
   though the unlock-floor *mechanism* stays the same kind of gate).
2. Layer Elite variants onto existing families first (cheap — stats +
   one ability, reuses existing portraits with a recolor/hint tweak
   rather than all-new art).
3. Build Mini-Boss mechanics one family at a time, starting with floors
   1-10 (Slime/Goblin/Rat/Wolf) since that's the range new players see
   first.
4. Bosses last — they're the most expensive per-entry (full kit + phases
   + unique art) and the floor ranges where they'd land (10, 20, 30...)
   are further out anyway.

**Sequencing recommendation:** given how much manual back-and-forth the
last monster-art pass took (silhouette bias, sexualization fixes, style
drift — see this session's history), don't try to batch all ~100+ new
entries at once. Ship floor 1-10's full tier set (Normal already done,
+Elite, +Goblin King miniboss, +floor-10 boss) end-to-end first, confirm
the art pipeline and combat-mechanic hooks both feel right, then repeat
per floor-range block.

**Open questions for you:**
- Is the floor-range table above final, or a starting point you expect
  to tweak once you see it in-game?
- Mini-boss/boss abilities — should there be a small reusable library of
  mechanics (summon-add, team-buff-aura, self-regen, enrage-at-low-hp)
  that different bosses mix and match, or fully bespoke scripting per
  named boss? (Reusable library is much cheaper to build and balance.)
- Swarm-style "100 goblins" framing — is this the same thing as the
  Survival Floor in section 1, or a separate idea (e.g. a boss floor that
  just has an unusually large *normal* enemy count, no survive-the-clock
  mechanic)?
