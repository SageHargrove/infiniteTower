# Team Status UI Specification

## Purpose
Enlarge the team status panel during battle/combat, fix hero face cropping in portraits, and surface mana values in the frontend which are currently only tracked in the backend.

## Context
- Battle and combat UI pages live in `frontend/src/pages/` (look for battle or combat-related page components)
- Hero portrait images are displayed inside the team status panel during fights
- Current problem: portraits are too small and faces are cut off at the sides due to incorrect sizing or CSS object-fit configuration
- Significant whitespace exists to the right of the team panel — this space should be consumed by expanding the panel
- Mana values are tracked in the backend (likely in `backend/services/battle_service.py` or equivalent) but never surfaced in the frontend
- Mana is a key resource for skill usage — hiding it from the player is a UX gap

## Requirements

### Requirement: Expanded Team Status Panel
The system SHALL expand the team status panel to use available horizontal whitespace during battle.

#### Scenario: Team Panel Uses Available Width
- GIVEN the player is on the battle/combat screen
- WHEN the team status panel is rendered
- THEN the panel SHALL expand to use the available horizontal space to its right
- AND the panel SHALL NOT overlap the battle log, enemy display, or action controls
- AND on a standard 1920×1080 viewport, the team panel SHALL be at least 20% wider than its current size

#### Scenario: Responsive Layout Maintained
- GIVEN the player resizes the browser window
- WHEN the team status panel re-renders
- THEN the panel SHALL scale proportionally without overflowing its container
- AND on narrow viewports (< 768px), the panel SHOULD stack vertically below the battle scene

---

### Requirement: Hero Portraits Displayed Without Face Cropping
The system SHALL render hero portrait images in the team status panel such that the hero's face is fully visible.

#### Scenario: Portrait Renders Without Horizontal Clipping
- GIVEN a hero is assigned to the active team
- WHEN their portrait appears in the team status panel
- THEN the portrait image SHALL be displayed using CSS `object-fit: contain` or equivalent
- AND the hero face SHALL NOT be clipped at the left or right edges
- AND the portrait container SHALL maintain a consistent aspect ratio (e.g., 2:3 portrait aspect)

#### Scenario: Larger Portrait Size
- GIVEN the expanded team panel
- WHEN hero portraits are rendered within it
- THEN each portrait SHALL be at least 30% larger (in pixel dimensions) than the current size
- AND portraits SHALL remain legible and not pixelated at the new size (use appropriately sized source images)

#### Scenario: Portrait Placeholder for Unassigned Slots
- GIVEN a team slot is empty (no hero assigned)
- WHEN the team status panel renders
- THEN an empty slot indicator (ghost outline or dark placeholder) SHALL be shown
- AND no broken image or error state SHALL appear

---

### Requirement: Mana Display in Frontend
The system SHALL surface each hero's current mana value in the team status panel during battle.

#### Scenario: Mana Value Retrieved from Backend
- GIVEN a battle is in progress
- WHEN the frontend fetches battle state (e.g., via polling or WebSocket)
- THEN the API response SHALL include each hero's `current_mana` and `max_mana` fields
- AND these values SHALL be sourced from the backend battle state (e.g., `battle_service.py` hero state)

#### Scenario: Mana Bar Rendered Per Hero
- GIVEN battle state data includes mana values
- WHEN the team status panel renders each hero card
- THEN a mana bar SHALL be displayed below or alongside the HP bar
- AND the mana bar SHALL visually reflect `current_mana / max_mana` as a filled progress bar
- AND the mana bar color SHALL be distinct from the HP bar (e.g., blue for mana, red/green for HP)

#### Scenario: Mana Value Tooltip or Label
- GIVEN the mana bar is rendered
- WHEN the player hovers over or inspects the mana bar
- THEN a tooltip or inline label SHALL display the exact values (e.g., "MP: 45 / 100")
- AND this label SHALL update in real-time as mana changes during battle

#### Scenario: Mana Depletes When Skill Used
- GIVEN a hero uses a skill in battle
- WHEN the backend processes the skill action and deducts mana
- THEN the frontend mana bar SHALL update on the next state refresh to reflect the reduced mana
- AND if `current_mana < skill_cost`, the skill button (if present) SHALL appear disabled or greyed out

---

### Requirement: Hero Status Information Layout
The system SHALL organize hero status information clearly within the enlarged panel.

#### Scenario: Status Panel Card Layout Per Hero
- GIVEN the team status panel is rendered
- WHEN a hero slot is populated
- THEN each hero card within the panel SHALL display (top to bottom):
  1. Hero portrait (large, unclipped)
  2. Hero name
  3. HP bar with value label
  4. Mana bar with value label
  5. Status effect icons (if any active buffs/debuffs)
- AND all elements SHALL be legible at the panel's rendered size
