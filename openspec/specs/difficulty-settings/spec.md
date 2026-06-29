# Difficulty Settings Specification

## Purpose
Add a difficulty selection step during new profile creation that affects enemy scaling, floor rewards, and leaderboard eligibility — without breaking existing profiles which should be treated as Normal difficulty.

## Context
- Profile creation logic is in `backend/routers/profiles.py` and associated backend models in `backend/models/`
- Frontend profile selection is in `frontend/src/components/ProfileSelect.jsx`
- Current behavior: all profiles use identical enemy scaling (Normal difficulty implicitly)
- Difficulty must be a profile-level setting — not session-level — so it persists and cannot be changed post-creation (or can only be changed via a specific mechanic with consequences)
- Existing profiles MUST NOT be broken: they should inherit `difficulty: "normal"` automatically during any migration
- Difficulty ties into PvP events: Hard mode players compete in separate leaderboards or receive handicaps

## Requirements

### Requirement: Difficulty Selection at Profile Creation
The system SHALL present a difficulty selection screen during new profile creation.

#### Scenario: New Player Creates Profile — Difficulty Screen Shown
- GIVEN a player clicks "Create New Profile" in `ProfileSelect.jsx`
- WHEN the profile creation flow begins
- THEN a difficulty selection step SHALL be shown before the profile is created
- AND three options SHALL be presented: Easy, Normal, Hard
- AND each option SHALL display a brief description of its effects (enemy strength, rewards, leaderboard eligibility)

#### Scenario: Player Selects Easy Difficulty
- GIVEN a player is on the difficulty selection screen
- WHEN they select "Easy" and confirm profile creation
- THEN the profile SHALL be created with `difficulty: "easy"` stored in the profile record
- AND a disclaimer SHALL inform the player: "Easy mode profiles are not eligible for leaderboard rankings"

#### Scenario: Player Selects Normal Difficulty
- GIVEN a player selects "Normal"
- WHEN the profile is created
- THEN the profile SHALL be created with `difficulty: "normal"`
- AND no disclaimer is required; this is the baseline experience

#### Scenario: Player Selects Hard Difficulty
- GIVEN a player selects "Hard"
- WHEN the profile is created
- THEN the profile SHALL be created with `difficulty: "hard"`
- AND a message SHALL inform the player: "Hard mode: stronger enemies, better loot, full leaderboard access"
- AND optionally, a confirmation prompt SHOULD warn the player that Hard mode is significantly more challenging

---

### Requirement: Difficulty Affects Enemy Scaling
The system SHALL apply difficulty-based multipliers to enemy stats during floor battles.

#### Scenario: Easy Mode — Reduced Enemy Stats
- GIVEN a profile with `difficulty: "easy"`
- WHEN a floor battle is initialized
- THEN enemy HP, attack, and defense stats SHALL be multiplied by a configurable easy-mode reduction factor (e.g., 0.75 — 25% weaker than Normal)
- AND this multiplier SHALL apply uniformly to all enemies including bosses

#### Scenario: Normal Mode — Baseline Enemy Stats
- GIVEN a profile with `difficulty: "normal"`
- WHEN a floor battle is initialized
- THEN enemy stats SHALL use the baseline values with no multiplier applied (×1.0)

#### Scenario: Hard Mode — Increased Enemy Stats
- GIVEN a profile with `difficulty: "hard"`
- WHEN a floor battle is initialized
- THEN enemy HP, attack, and defense stats SHALL be multiplied by a hard-mode increase factor (e.g., 1.35 — 35% stronger than Normal)
- AND bosses SHALL receive an additional hard-mode stat bonus on top of their standard boss padding

---

### Requirement: Difficulty Affects Floor Rewards
The system SHALL scale floor rewards based on the profile's difficulty setting.

#### Scenario: Easy Mode — Increased Gold, Reduced Rare Drops
- GIVEN a profile with `difficulty: "easy"`
- WHEN a floor is cleared
- THEN gold rewards SHALL be increased by a configurable bonus (e.g., +25% gold)
- AND rare drop rates (equipment grade A+/S/S+, hero summoning tokens) SHALL be reduced by a configurable penalty (e.g., −30%)
- AND this trade-off SHALL be clearly communicated in the difficulty description at profile creation

#### Scenario: Normal Mode — Baseline Rewards
- GIVEN a profile with `difficulty: "normal"`
- WHEN a floor is cleared
- THEN rewards SHALL use the standard drop table with no multiplier

#### Scenario: Hard Mode — Improved Rare Drops, Standard Gold
- GIVEN a profile with `difficulty: "hard"`
- WHEN a floor is cleared
- THEN rare drop rates SHALL be increased by a configurable bonus (e.g., +40% for A+ and above equipment, +20% hero token drop chance)
- AND gold rewards SHALL remain at baseline (Hard mode's appeal is quality loot, not quantity)

---

### Requirement: Leaderboard Eligibility Based on Difficulty
The system SHALL enforce leaderboard eligibility rules based on difficulty.

#### Scenario: Easy Mode Profile Cannot Access Leaderboard
- GIVEN a profile with `difficulty: "easy"`
- WHEN the player navigates to any leaderboard or PvP event page
- THEN their profile SHALL be shown as "Not Eligible" with an explanation (difficulty restriction)
- AND they SHALL NOT be able to submit scores or enter ranked events

#### Scenario: Normal Mode — Standard Leaderboard Access
- GIVEN a profile with `difficulty: "normal"`
- WHEN the player views the leaderboard
- THEN they SHALL appear in the standard leaderboard pool
- AND they SHALL be eligible to enter PvP events with Normal-tier rewards

#### Scenario: Hard Mode — Full Leaderboard Access with Separate Tier
- GIVEN a profile with `difficulty: "hard"`
- WHEN the player views the leaderboard
- THEN they SHALL appear in a separate "Hard Mode" leaderboard tier
- AND Hard mode rankings SHALL be displayed above Normal rankings as a mark of prestige
- AND Hard mode PvP event rewards SHALL be superior to Normal mode rewards

---

### Requirement: Existing Profiles Inherit Normal Difficulty
The system SHALL automatically assign `difficulty: "normal"` to any existing profile that lacks a difficulty field.

#### Scenario: Migration — Existing Profile Loaded Without Difficulty Field
- GIVEN an existing profile record that was created before the difficulty system was added
- WHEN the backend loads that profile from the database
- THEN the profile SHALL behave as if `difficulty: "normal"` is set
- AND the backend SHALL either write `"normal"` to the profile record on next save OR handle the missing field via a default at the model level in `backend/models/`
- AND no existing profile SHALL be deleted, reset, or broken

#### Scenario: Profile Model Default Value
- GIVEN the profile model definition in `backend/models/`
- WHEN a developer inspects the `difficulty` field
- THEN it SHALL have a default value of `"normal"` so missing values are automatically handled without a migration script

---

### Requirement: Difficulty Cannot Be Changed After Profile Creation
The system SHALL prevent players from changing their difficulty setting post-creation (unless a specific unlock mechanic is designed).

#### Scenario: Player Attempts to Change Difficulty In-Game
- GIVEN a profile already created with any difficulty
- WHEN the player looks for a difficulty setting in their profile or settings page
- THEN no difficulty change option SHALL be available (difficulty is read-only)
- AND the current difficulty SHALL be displayed as an informational badge (e.g., "This profile: Normal Mode")

#### Scenario: Developer Override (Admin Only)
- GIVEN a backend admin endpoint or CLI tool is available
- WHEN an admin changes a profile's difficulty via the admin interface
- THEN the change SHALL be persisted and the new difficulty applied on the next floor battle
- AND this admin capability SHALL NOT be exposed to regular players via the frontend
