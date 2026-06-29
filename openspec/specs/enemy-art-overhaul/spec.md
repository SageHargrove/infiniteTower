# Enemy Art Overhaul Specification

## Purpose
Replace the "Slime" and "Giant Rat" enemy types with thematically appropriate dark fantasy enemies
whose silhouettes and forms render well as AI-generated art. These two enemy types consistently
look cartoonish and out of place in the Solo Leveling-inspired aesthetic.

## Context
- Enemy art is generated via `generate_image` and stored in `backend/static/enemies/`
- Enemy types are defined in the database and referenced in `backend/services/battle_service.py`
- Slimes and rats are inherently "cute" designs that clash with the game's brutal, dark tone
- AI image generation handles humanoid creatures, angular/geometric shapes, and shadowy forms
  much better than round, amorphous or rodent shapes

## Proposed Replacements

### Replace: Slime → Shadow Wisp
A small, hovering mass of condensed shadow energy — wispy tendrils, faint purple glow,
no solid form. Early floor enemy. Renders excellently as AI art (shadowy, ethereal, angular).

### Replace: Giant Rat → Dungeon Imp
A small, wiry demonic creature with leathery skin, hunched posture, small horns.
Classic dungeon-tier enemy consistent with the tower's dark fantasy setting.
Renders well (humanoid proportions, defined silhouette).

## Additional Early-Floor Enemy Candidates
These can replace or supplement if more variety is needed:
- **Bone Crawler** — skeletal insectoid creature, good for floors 1–5
- **Stone Shard Golem** — small animated rock construct, angular and easy to generate
- **Cave Wraith** — translucent ghostly humanoid, wispy and atmospheric
- **Iron Spider** — large dark metallic spider, geometric shape renders cleanly

## Requirements

### Requirement: Remove Slime enemy type
The system SHALL replace all references to "Slime" with "Shadow Wisp" throughout the codebase
and database, generating new appropriate artwork.

#### Scenario: Shadow Wisp appears on early floors
- GIVEN a player is on floors 1–10
- WHEN an enemy encounter is generated
- THEN "Shadow Wisp" may appear as a common enemy
- AND its artwork shows a hovering dark shadowy form with purple energy

#### Scenario: Shadow Wisp art generation
- GIVEN the enemy art generation script runs
- WHEN generating art for "Shadow Wisp"
- THEN the prompt uses: "dark fantasy shadowy wisp creature, hovering ball of dark energy with wispy tendrils, faint purple glow, black background, concept art style, no text"
- AND the result is stored as `backend/static/enemies/Shadow Wisp.png`

### Requirement: Remove Giant Rat enemy type
The system SHALL replace all references to "Giant Rat" with "Dungeon Imp" throughout the codebase
and database, generating new appropriate artwork.

#### Scenario: Dungeon Imp appears on early floors
- GIVEN a player is on floors 1–15
- WHEN an enemy encounter is generated
- THEN "Dungeon Imp" may appear as a common enemy
- AND its artwork shows a small wiry demonic creature with hunched posture

#### Scenario: Dungeon Imp art generation
- GIVEN the enemy art generation script runs
- WHEN generating art for "Dungeon Imp"
- THEN the prompt uses: "dark fantasy dungeon imp creature, small wiry demon with leathery skin, small horns, hunched posture, glowing red eyes, black background, concept art style, no text"
- AND the result is stored as `backend/static/enemies/Dungeon Imp.png`

### Requirement: Database migration
The system SHALL update existing enemy entries in the database without breaking active game saves.

#### Scenario: Existing profiles with Slime/Rat kill counts
- GIVEN a profile has kill counts recorded for "Slime" or "Giant Rat"
- WHEN the migration runs
- THEN those records are renamed to the new enemy names
- AND kill count totals are preserved

### Requirement: Consistent dark fantasy aesthetic
The system SHALL ensure all early-floor enemies fit the dark tower aesthetic.

#### Scenario: Art review gate
- GIVEN new enemy art is generated
- WHEN the art is reviewed
- THEN no enemy should appear cartoonish, cute, or inconsistent with a grim dark fantasy tone
- AND enemies should have a clear readable silhouette at small display sizes
