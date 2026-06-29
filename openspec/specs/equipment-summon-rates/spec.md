# Equipment Summon Rates Specification

## Purpose
Reweight equipment gacha pull rates so that rarer grades are exponentially less common, matching the manhwa-accurate difficulty curve applied to hero gacha rates.

## Context
- Equipment gacha logic lives in `backend/services/gacha_service.py`
- Equipment pull endpoints are defined in `backend/routers/gacha.py`
- Equipment grades (ascending rarity): F, E, D, C, B, B+, A, A+, S, S+
- Current rates are insufficiently differentiated — B+ should be dramatically rarer than B, not marginally rarer
- Hero gacha already uses an exponential curve; equipment must match this philosophy to preserve the game's power economy
- Players grinding for S+ equipment should feel the same awe as pulling a 5★+ hero

## Requirements

### Requirement: Exponential Rate Curve for Equipment Grades
The system SHALL assign pull probabilities to equipment grades using an exponential decay curve, so that each grade above a threshold is significantly rarer than the one below.

#### Scenario: F-Grade Equipment Rate (Most Common)
- GIVEN a player initiates an equipment gacha pull
- WHEN the random roll is evaluated in `gacha_service.py`
- THEN F-grade equipment SHALL have the highest pull probability (e.g., ~40%)
- AND F-grade items SHALL feel expected/common so they serve as bulk filler

#### Scenario: E-Grade Equipment Rate
- GIVEN a player initiates an equipment gacha pull
- WHEN the random roll is evaluated
- THEN E-grade equipment SHALL have approximately ~25% probability
- AND E + F combined SHALL account for ~65% of all pulls

#### Scenario: D-Grade Equipment Rate
- GIVEN a player initiates an equipment gacha pull
- WHEN the random roll is evaluated
- THEN D-grade equipment SHALL have approximately ~15% probability

#### Scenario: C-Grade Equipment Rate
- GIVEN a player initiates an equipment gacha pull
- WHEN the random roll is evaluated
- THEN C-grade equipment SHALL have approximately ~10% probability

#### Scenario: B-Grade Equipment Rate
- GIVEN a player initiates an equipment gacha pull
- WHEN the random roll is evaluated
- THEN B-grade equipment SHALL have approximately ~5% probability

#### Scenario: B+ Grade Equipment Rate — Meaningful Rarity Gap
- GIVEN a player initiates an equipment gacha pull
- WHEN the random roll is evaluated
- THEN B+-grade equipment SHALL have approximately ~2.5% probability
- AND this rate SHALL feel noticeably rarer than B — not a minor drop (i.e., must be at least 40–50% fewer than B)
- AND obtaining B+ equipment SHALL register as a minor success moment for the player

#### Scenario: A-Grade Equipment Rate
- GIVEN a player initiates an equipment gacha pull
- WHEN the random roll is evaluated
- THEN A-grade equipment SHALL have approximately ~1.5% probability

#### Scenario: A+-Grade Equipment Rate
- GIVEN a player initiates an equipment gacha pull
- WHEN the random roll is evaluated
- THEN A+-grade equipment SHALL have approximately ~0.75% probability

#### Scenario: S-Grade Equipment Rate
- GIVEN a player initiates an equipment gacha pull
- WHEN the random roll is evaluated
- THEN S-grade equipment SHALL have approximately ~0.2% probability
- AND pulling an S-grade item SHALL be a rare, celebratory event

#### Scenario: S+-Grade Equipment Rate (Ultra Rare)
- GIVEN a player initiates an equipment gacha pull
- WHEN the random roll is evaluated
- THEN S+-grade equipment SHALL have approximately ~0.05% probability
- AND S+ equipment SHALL be the rarest obtainable item in the equipment gacha
- AND the game SHOULD display a special animation or notification on S+ pulls

---

### Requirement: Rates Sum to 100%
The system SHALL ensure that all equipment grade probabilities sum to exactly 100%.

#### Scenario: Rate Table Validation
- GIVEN the rate table defined in `gacha_service.py`
- WHEN the gacha service is initialized or rates are updated
- THEN the sum of all equipment grade probabilities SHALL equal 1.0 (100%)
- AND any rounding adjustments SHALL be applied to the most common tier (F)

---

### Requirement: Pity System for Equipment (Optional but Specced)
The system SHALL support a soft pity mechanism for equipment gacha at a defined pull threshold.

#### Scenario: Soft Pity Activates for A+ or Above
- GIVEN a player has made 80 or more consecutive equipment pulls without receiving A+ or above
- WHEN the next pull is rolled
- THEN the probability of A+ or higher SHALL be increased by a configurable multiplier (e.g., 2x base rate)
- AND this pity counter SHALL reset upon receiving any A+ or higher item

#### Scenario: Hard Pity Guarantees S-Grade
- GIVEN a player has made 150 or more consecutive equipment pulls without receiving S-grade or above
- WHEN the next pull is rolled
- THEN the result SHALL be forced to S-grade or S+
- AND the pity counter SHALL reset
- AND the pity count SHALL be persisted in the player's profile data

---

### Requirement: Rate Display in UI
The system SHALL expose accurate equipment pull rates to the player.

#### Scenario: Player Views Equipment Pull Rates
- GIVEN a player is on the equipment gacha screen
- WHEN they open the "Rate Details" or equivalent info panel
- THEN all grade probabilities SHALL be displayed accurately
- AND S+ SHALL be listed with its exact probability (e.g., "0.05%")
- AND pity thresholds SHALL be displayed if the pity system is enabled

---

### Requirement: Rate Configuration Is Centralized
The system SHALL define equipment grade rates in a single configuration object or dict, not scattered inline.

#### Scenario: Rate Config is Editable
- GIVEN a developer needs to adjust grade rates
- WHEN they open `backend/services/gacha_service.py`
- THEN the equipment rates SHALL be defined in a single dict/config block (e.g., `EQUIPMENT_RATES = {...}`)
- AND no rate values SHALL be hardcoded outside of this config block
