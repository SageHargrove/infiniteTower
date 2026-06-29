# Talent Observatory Specification

## Purpose
Implement a new base facility called the "Talent Observatory" that allows players to reveal the hidden "Talent" stat of their heroes. This provides a gold sink and a progression mechanic where players gradually uncover the true potential of their roster by upgrading the facility.

## Context
- The facility will be part of the player's base/town upgrades.
- Heroes currently have a hidden 'Talent' stat (0-100) that affects their stat growth. 
- The user currently cannot see this stat natively. The Talent Observatory allows them to reveal it permanently for a cost.
- The cost to reveal the talent scales with the hero's star level.
- The detail of the revelation (vague tier -> range -> exact number) scales with the Talent Observatory's building level.

## Requirements

### Requirement: Building Concept & Upgrades
The system SHALL implement the Talent Observatory as an upgradeable facility with three distinct levels of function.

#### Scenario: Level 1 - Qualitative Tier
- GIVEN the Talent Observatory is at Level 1
- WHEN a player pays to reveal a hero's talent
- THEN the system SHALL reveal a vague qualitative tier (e.g., 'Poor', 'Average', 'Good', 'Exceptional') based on the hidden numerical value.
- AND this tier SHALL be saved to the hero's profile and displayed in the UI.

#### Scenario: Level 2 - Specific Range
- GIVEN the Talent Observatory is at Level 2
- WHEN a player pays to reveal a hero's talent
- THEN the system SHALL reveal a specific numerical range (e.g., 'Talent is between 70-85').
- AND this range SHALL be saved to the hero's profile and displayed in the UI.

#### Scenario: Level 3 - Exact Number
- GIVEN the Talent Observatory is at Level 3
- WHEN a player pays to reveal a hero's talent
- THEN the system SHALL reveal the exact numerical Talent stat (e.g., 'Talent is 82').
- AND this exact number SHALL be saved to the hero's profile and displayed in the UI.

---

### Requirement: Backend Requirements (FastAPI)
The backend SHALL handle the logic for calculating costs, determining the revealed string based on the facility level, and saving the state.

#### Scenario: Facility Database
- GIVEN the facility database schema
- WHEN the backend initializes or updates
- THEN the 'Talent Observatory' SHALL be included in the list of upgradeable facilities with its associated upgrade costs and level caps.

#### Scenario: Reveal Endpoint
- GIVEN an endpoint `/api/facilities/talent_observatory/reveal`
- WHEN a valid `hero_id` is passed via a POST request
- THEN the backend SHALL calculate the gold cost as `hero_star_level * 500` (or similar configured scaling).
- AND the backend SHALL deduct this cost from the player's inventory.
- AND the backend SHALL calculate the string/data to return to the player (Tier, Range, or Exact Number) based on the current level of the Talent Observatory.
- AND the backend SHALL save the 'revealed' status to the hero's database entry.

---

### Requirement: Frontend Requirements (React)
The frontend SHALL provide a UI for players to interact with the Talent Observatory and see their revealed talents.

#### Scenario: Talent Observatory Component
- GIVEN the React frontend
- WHEN the player navigates to the Talent Observatory facility
- THEN a new component `TalentObservatory.jsx` SHALL be rendered.
- AND the UI SHALL show a list of the player's heroes.

#### Scenario: Interaction & Costs
- GIVEN the Talent Observatory UI
- WHEN a hero is selected
- THEN the UI SHALL display the calculated gold cost to reveal their talent.
- AND an 'Awaken' button SHALL be available to call the backend API.

#### Scenario: Displaying Revealed Talents
- GIVEN a hero whose talent has already been revealed
- WHEN they are viewed in the Talent Observatory or the main Hero roster
- THEN the UI SHALL display the result (Tier, Range, or Exact based on the building's highest achieved level at the time of revelation) instead of the 'Awaken' button.

#### Scenario: Upgrading the Shrine
- GIVEN the standard facility upgrade UI
- WHEN the player selects the Talent Observatory
- THEN the building SHALL be upgradeable up to Level 3 using the standard material/gold costs.
