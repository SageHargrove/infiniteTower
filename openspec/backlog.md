# Backlog

Deferred items — confirmed real, not started, no timeline. Pulled from the
2026-06-26 to 2026-06-29 Discord feedback review. Pick items off this list
when ready; nothing here is scheduled.

## Art / Content
- **Enemy art audit**: go through every enemy's generated portrait, find
  which prompts produce broken/off-model art, fix the prompt or replace
  the enemy concept. Slime -> Shadow Wisp and Giant Rat -> Dungeon Imp
  (enemy-art-overhaul) were the only two addressed so far.
- **Dragon-tier higher-ranked enemies**: a normal "Young Dragon"/"Dracolich"
  exist; want elite/boss-ranked dragon variants.
- **Evil 7-star-looking humanoid elite/boss**: 7-star hero art generates
  well; want a dedicated evil-humanoid enemy concept that leans on the same
  thing that makes 7-star hero art read well.
- **Monster art pipeline / LoRA investigation**: monster-type prompts keep
  generating humanoid results instead of actual monster shapes. Needs
  investigating whether a monster-specific LoRA or different prompt
  structure is needed for the local ComfyUI pipeline.

## Floor Variety
- Floor types beyond combat are thin — survival/defend/escort/explore
  exist, but wanted: "war," "find and retrieve," and other distinct floor
  archetypes, not just combat dressed up differently.
- Lore readout before floor 10, or an unlockable lore page that grows as
  you climb.

## Skills Content
- **Bespoke skill kits per class**: only 6 classes (Warrior, Spearman,
  Thief, Archer, Mage, Magic Engineer) have a dedicated `SKILL_POOL` entry
  in `services/skills_service.py` — the other ~130 classes (Knight,
  Paladin, Necromancer, Acolyte, Cleric, etc.) all fall back to the shared
  `GENERIC_SKILLS` pool. Stopgapped for now (GENERIC_SKILLS bumped to 3
  actives + more passives, every 3★+ hero guaranteed at least one active),
  but the real ask is hundreds-to-thousands of unique skills long-term,
  weighted more passive than active, with passives leaning class-agnostic
  and actives leaning class-specific.

## Systems / Text Quality
- **LLM model for narrative text**: currently Gemini-based
  (services/llm_service.py). Investigate Haiku (or another model) for
  better text quality if Gemini Pro doesn't work out — user is
  independently testing this.
- **Secure coding / anti-cheat audit**: no review has been done on
  preventing save-file tampering, request forgery, or other client-side
  cheating vectors.

## Notes
- Each item above was independently confirmed missing (not just
  forgotten) via a code search before being added here — not guesses.
