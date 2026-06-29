# Hero Chatter Specification

## Purpose
Give each hero distinct dialogue and personality that varies by class and rarity, replacing the current uniform speech patterns so players feel emotionally connected to individual heroes.

## Context
- Hero data and class definitions exist in `backend/models/` (hero model likely defines class and rarity fields)
- UI components that display hero dialogue are in `frontend/src/components/`
- Currently all heroes share the same dialogue lines regardless of class or rarity — this undermines immersion and makes the roster feel homogeneous
- Target aesthetic: dark fantasy RPG (Solo Leveling / Tower of God inspiration) — speech should feel like it belongs in that genre
- Each dialogue variant should be authored as a template with hero-specific variable slots (name, class, etc.)

## Requirements

### Requirement: Class-Specific Speech Patterns
The system SHALL assign distinct speech patterns and vocabulary to each hero class, reflecting their archetype and role.

#### Scenario: Spearman Hero Speaks Militaristically
- GIVEN a hero with `class == "Spearman"`
- WHEN any dialogue event triggers for that hero
- THEN the selected dialogue line SHALL use military/tactical phrasing (e.g., "Hold the line.", "The formation breaks at their flank.", "I've faced worse on the northern wall.")
- AND metaphors SHALL relate to warfare, discipline, and strategic combat

#### Scenario: Acolyte Hero Speaks Spiritually
- GIVEN a hero with `class == "Acolyte"`
- WHEN any dialogue event triggers
- THEN dialogue SHALL reflect faith, devotion, and mystical awareness (e.g., "The Light guides my hand.", "Even in darkness, I sense the divine current.")
- AND references to prayer, rites, or spiritual duty SHOULD appear in battle and facility lines

#### Scenario: Mage Hero Speaks Intellectually
- GIVEN a hero with `class == "Mage"` or `"Arcanist"`
- WHEN any dialogue event triggers
- THEN dialogue SHALL be analytical, scholarly, and occasionally arrogant (e.g., "Predictable. Their formation has seventeen calculable weaknesses.", "You waste my time with easy targets.")

#### Scenario: Assassin/Rogue Hero Speaks Tersely
- GIVEN a hero with `class == "Assassin"` or `"Rogue"`
- WHEN any dialogue event triggers
- THEN dialogue SHALL be minimal, cold, and pragmatic (e.g., "Done.", "They never saw me.", "Next target?")
- AND no unnecessary words or elaborate speeches for this class

#### Scenario: Berserker/Warrior Hero Speaks Aggressively
- GIVEN a hero with `class == "Berserker"` or `"Warrior"`
- WHEN any dialogue event triggers
- THEN dialogue SHALL express raw aggression and bloodlust (e.g., "MORE! Give me more enemies!", "I live for this.")

---

### Requirement: Rarity-Based Confidence and Dramatic Tone
The system SHALL scale the confidence, gravitas, and dramatic flair of hero dialogue in proportion to their star rarity.

#### Scenario: 1★–2★ Hero — Humble and Uncertain
- GIVEN a hero with `star_rating <= 2`
- WHEN a dialogue event triggers
- THEN the dialogue SHALL express uncertainty, modesty, or beginner enthusiasm (e.g., "I'll try my best!", "Is... is this okay?", "I won't let you down, Master.")

#### Scenario: 3★–4★ Hero — Competent and Direct
- GIVEN a hero with `star_rating == 3` or `4`
- WHEN a dialogue event triggers
- THEN dialogue SHALL be confident but not grandiose (e.g., "Leave this to me.", "I've handled harder fights than this.")

#### Scenario: 5★ Hero — Elite Confidence
- GIVEN a hero with `star_rating == 5`
- WHEN a dialogue event triggers
- THEN dialogue SHALL convey elite power and measured intensity (e.g., "Don't get in my way. I'll handle this.", "You called for strength? Here I am.")

#### Scenario: 6★ Hero — Legendary Gravitas
- GIVEN a hero with `star_rating == 6`
- WHEN a dialogue event triggers
- THEN dialogue SHALL feel like the words of a legend — calm, immense, inevitable (e.g., "The outcome was decided the moment you called on me.", "Power like mine doesn't announce itself. It simply ends things.")

#### Scenario: 7★ Hero — Mythic / Overwhelming Presence
- GIVEN a hero with `star_rating == 7`
- WHEN a dialogue event triggers
- THEN dialogue SHALL convey cosmic, mythic weight — brief, absolute, or hauntingly philosophical (e.g., "I existed before your tower had a name.", "You don't summon me. I allow myself to appear.")

---

### Requirement: Dialogue Trigger Events
The system SHALL fire distinct dialogue lines for each of the following trigger events.

#### Scenario: Hero Summoned
- GIVEN a player pulls a new hero from the gacha
- WHEN the hero is summoned and their card reveal animation plays
- THEN the hero SHALL deliver a unique introduction line appropriate to their class and rarity
- AND this line SHALL be displayed on the summon result screen in `frontend/src/components/`

#### Scenario: Hero Assigned to Facility
- GIVEN a hero is assigned to a base facility (e.g., Training Grounds, Library, Workshop)
- WHEN the assignment is confirmed
- THEN the hero SHALL deliver a facility-specific reaction line (e.g., a warrior assigned to training: "Finally. I was growing restless.")
- AND the line SHALL reflect the hero's class relationship to the facility type

#### Scenario: Battle Victory
- GIVEN the player's team wins a floor battle
- WHEN the victory screen renders
- THEN at least one surviving hero SHALL deliver a post-battle line
- AND the selected hero SHALL be the highest-rarity survivor
- AND the line SHALL be victory-appropriate (triumphant, weary, or nonchalant depending on personality)

#### Scenario: Battle Defeat
- GIVEN the player's team loses a floor battle
- WHEN the defeat screen renders
- THEN a hero SHALL deliver a line reflecting defeat (never resigned, always defiant or retrospective)
- AND lower-rarity heroes SHOULD show fear/uncertainty; higher-rarity heroes SHOULD show cold resolve

#### Scenario: Hero Levels Up
- GIVEN a hero gains enough XP to level up
- WHEN the level-up event fires
- THEN the hero SHALL deliver a level-up line appropriate to their class/rarity
- AND the line SHALL feel like personal growth (e.g., warrior: "My strikes grow sharper.", acolyte: "The light blesses this ascent.")

---

### Requirement: Dialogue Data Structure
The system SHALL store hero dialogue in a structured, extensible format accessible to the frontend.

#### Scenario: Dialogue Defined Per Class and Rarity Tier
- GIVEN a developer adds a new dialogue line
- WHEN they open the dialogue data source (e.g., a JSON file, Python model, or JS constant)
- THEN they SHALL find dialogue organized by: `{ class: { rarity_tier: { event: [lines] } } }`
- AND random selection from the available lines for a given class/rarity/event SHALL be handled by a utility function

#### Scenario: Fallback Dialogue If Class/Rarity Combo Missing
- GIVEN a hero has a class or rarity that lacks specific dialogue
- WHEN a dialogue event triggers
- THEN a generic fallback line SHALL be displayed
- AND no UI error or empty string SHALL appear
