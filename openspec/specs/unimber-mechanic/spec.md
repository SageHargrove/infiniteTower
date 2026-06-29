# Unimber Mechanic Specification

## Purpose
Implement the "Unimber" battle mechanic: when a hero faces multiple enemies alone, they take significantly increased damage per additional enemy — but a sufficiently powerful hero can still hard-carry through sheer strength, enabling power fantasy moments while punishing weak solo attempts.

## Context
- Core combat logic lives in `backend/services/battle_service.py` (or equivalent combat module)
- Current battle system does not apply damage multipliers based on the outnumbering ratio
- The mechanic must balance two competing design goals:
  1. **Danger**: Being outnumbered is genuinely threatening and creates meaningful tension
  2. **Power Fantasy**: A 6★ or 7★ hero with enough stats can still overcome being outnumbered — rewarding investment
- Bosses also benefit from this mechanic from the enemy side: when a boss faces a full 5-hero team, the heroes collectively apply this mechanic to the boss (stat padding)
- Named "Unimber" — evocative of unleashing, bearing great weight, or being unleashed under pressure

## Requirements

### Requirement: Unimber Damage Multiplier — Solo Hero vs. Multiple Enemies
The system SHALL apply a stacking damage multiplier to a hero when they are the sole surviving hero facing multiple enemies.

#### Scenario: 1 Hero vs. 2 Enemies
- GIVEN a battle where only 1 hero remains alive on the player's side
- AND there are 2 enemies still active
- WHEN damage is calculated for an enemy attacking that hero
- THEN the hero SHALL receive a 40% damage increase (incoming damage × 1.40)
- AND this multiplier SHALL be labeled "Unimber ×1" in the battle log

#### Scenario: 1 Hero vs. 3 Enemies
- GIVEN only 1 player hero remains
- AND there are 3 enemies active
- WHEN damage is calculated
- THEN the hero SHALL receive a 80% damage increase (incoming damage × 1.80) — stacking 40% per extra enemy above 1
- AND the multiplier SHALL be labeled "Unimber ×2" in the battle log

#### Scenario: 1 Hero vs. 4 Enemies
- GIVEN only 1 player hero remains
- AND there are 4 enemies active
- WHEN damage is calculated
- THEN the hero SHALL receive a 120% damage increase (incoming damage × 2.20)
- AND the multiplier SHALL be labeled "Unimber ×3"

#### Scenario: 1 Hero vs. 5 Enemies (Maximum Standard)
- GIVEN only 1 player hero remains
- AND there are 5 enemies active
- WHEN damage is calculated
- THEN the hero SHALL receive a 160% damage increase (incoming damage × 2.60)
- AND the multiplier SHALL be labeled "Unimber ×4"
- AND this is the expected maximum for standard combat (5 enemies total)

#### Scenario: Multiplier Formula
- GIVEN `N` = number of active enemies, `H` = number of active player heroes
- WHEN `H == 1` and `N > 1`
- THEN Unimber multiplier = `1.0 + (0.40 × (N - 1))`
- AND when `H > 1`, no Unimber multiplier SHALL be applied (mechanic only triggers for solo heroes)

---

### Requirement: Power Fantasy — Strong Hero Can Still Carry
The system SHALL NOT make Unimber an automatic loss condition; a sufficiently powerful hero must still be able to win.

#### Scenario: High-Stat Hero Survives Unimber Damage
- GIVEN a 6★ or 7★ hero with very high defense and HP stats faces 4 enemies alone
- WHEN Unimber damage multipliers are applied
- THEN the hero's combat math SHALL still allow survival if their raw stats justify it
- AND no artificial damage cap or forced death mechanic SHALL override normal damage calculation
- AND the player's investment in hero strength SHALL remain the primary determinant of outcome

#### Scenario: Unimber Does Not Stack Beyond Enemies Present
- GIVEN 1 hero faces 5 enemies
- WHEN 2 enemies are defeated mid-battle, leaving 3 remaining
- THEN the Unimber multiplier SHALL update dynamically to reflect 3 enemies (×2 → 80% bonus)
- AND the multiplier SHALL NOT remain at the peak value from earlier in the battle

---

### Requirement: Battle Log Transparency
The system SHALL communicate the Unimber effect to the player during combat.

#### Scenario: Unimber Status Shown in Battle Log
- GIVEN the Unimber mechanic activates
- WHEN a damage event is logged
- THEN the battle log entry SHALL include the Unimber multiplier (e.g., "[Unimber ×2] Enemy Orc dealt 350 damage!")
- AND the hero's status display SHALL show an "Unimber" debuff icon while active

#### Scenario: Unimber Deactivates When Allies Revive or Enter
- GIVEN a hero is under Unimber conditions
- WHEN a second hero becomes active (e.g., via a revival mechanic or future support feature)
- THEN the Unimber multiplier SHALL immediately drop to 0 (not apply)
- AND the battle log SHALL note "Unimber lifted — reinforcement arrived"

---

### Requirement: Boss Stat Padding via Unimber (Enemy Side)
The system SHALL apply a mirrored Unimber-like stat pad to boss enemies when they face a full 5-hero team.

#### Scenario: Boss Faces 5 Heroes — Stat Padding Applied
- GIVEN a floor contains a boss enemy
- AND the player fields a full team of 5 heroes
- WHEN the boss's combat stats are initialized
- THEN the boss SHALL receive a stat padding multiplier to HP and defense (e.g., +20% HP and +10% defense per hero above 1, up to a configured cap)
- AND this padding SHALL scale with the number of player heroes, not be a flat bonus
- AND the padding SHALL be noted in the floor info panel (e.g., "Boss Empowered: Full party detected")

#### Scenario: Boss Stat Padding is Configurable Per Floor
- GIVEN a floor definition in the backend
- WHEN the floor's boss is initialized
- THEN the boss stat padding coefficient SHALL be configurable per floor (some bosses are more pack-aware than others)
- AND a default multiplier SHALL be used if no per-floor override is specified

---

### Requirement: Mechanic Configuration
The system SHALL store Unimber multiplier constants in a configurable location, not hardcoded inline.

#### Scenario: Unimber Config Defined in Battle Service
- GIVEN a developer opens `backend/services/battle_service.py`
- WHEN they search for Unimber constants
- THEN they SHALL find a config block or constant (e.g., `UNIMBER_DAMAGE_PER_EXTRA_ENEMY = 0.40`)
- AND adjusting this value SHALL affect all Unimber calculations without any other code changes
