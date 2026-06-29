# Base Hierarchy Frontend Specification

## Purpose
Update the Base Hierarchy frontend tab to accurately visualize the logarithmic scaling that the backend already uses for hierarchy calculations, showing the proper diminishing returns curve to players.

## Context
- Frontend: `frontend/src/pages/BasePage.jsx` — renders the Base tab including the hierarchy panel
- Backend: `backend/routers/base.py` — returns hierarchy data with logarithmic scaling applied
- Current problem: the frontend either shows hierarchy levels linearly or without clear visual indication of the logarithmic curve, misleading players about progression effort
- Logarithmic scaling means: early levels are cheap/fast; later levels cost exponentially more and yield diminishing stat gains
- This visual must convey "the grind gets harder" honestly and clearly while still motivating players

## Requirements

### Requirement: Visual Curve Accurately Reflects Logarithmic Progression
The system SHALL render hierarchy progression using a visual that reflects logarithmic diminishing returns, not a linear scale.

#### Scenario: Hierarchy Progress Chart Uses Logarithmic Y-Axis or Curve
- GIVEN the player navigates to the Base tab in `BasePage.jsx`
- WHEN the hierarchy section is rendered
- THEN any progress chart, bar, or graph for hierarchy levels SHALL use a logarithmic representation
- AND the visual slope SHALL be steep at low levels (fast early gains) and flatten noticeably at high levels
- AND the chart SHALL NOT imply that going from level 50→51 costs the same as level 1→2

#### Scenario: XP/Cost Per Level Shown on Curve
- GIVEN the hierarchy chart is rendered
- WHEN the player inspects a specific level on the progression curve
- THEN a tooltip or label SHALL display the XP/cost required to reach that level from the previous one
- AND the cost values SHALL match the backend calculation in `base.py` exactly

#### Scenario: Player's Current Level Marked on Curve
- GIVEN the player has a current hierarchy level
- WHEN they view the hierarchy progression chart
- THEN their current level SHALL be clearly marked (e.g., a glowing dot, vertical line, or highlighted segment)
- AND their position on the logarithmic curve SHALL visually contextualize how far along the diminishing returns they are

---

### Requirement: Diminishing Returns Explained to Player
The system SHALL communicate the concept of diminishing returns to the player in plain language within the UI.

#### Scenario: Diminishing Returns Label or Callout
- GIVEN the hierarchy progression display is visible
- WHEN the player views the chart
- THEN a brief descriptive label SHALL appear near the flattening portion of the curve (e.g., "Gains diminish significantly after Level 50")
- AND this threshold level SHALL be dynamically read from backend data, not hardcoded in the frontend

#### Scenario: Stat Gain Per Level Shown Alongside Hierarchy Level
- GIVEN the player views the hierarchy data
- WHEN the panel renders
- THEN the stat gain per hierarchy level SHALL be shown (e.g., "+X% base stats at Level N")
- AND these values SHALL decrease visibly as levels increase, reinforcing the diminishing returns message

---

### Requirement: Backend Data Drives All Hierarchy Values
The system SHALL derive all displayed hierarchy values from the backend response, with no frontend-side recalculation.

#### Scenario: Frontend Fetches Hierarchy Data from Backend
- GIVEN the player opens the Base tab
- WHEN `BasePage.jsx` initializes
- THEN it SHALL fetch hierarchy data from the API endpoint defined in `backend/routers/base.py`
- AND the response SHALL include at minimum: `current_level`, `current_xp`, `xp_to_next_level`, `levels[]` array with cost and stat_gain per level

#### Scenario: No Hardcoded Progression Values in Frontend
- GIVEN a developer inspects `BasePage.jsx`
- WHEN they search for XP cost or stat gain constants
- THEN no hardcoded progression values SHALL be found in the frontend code
- AND all such values SHALL come from the backend API response

---

### Requirement: Chart Library or Canvas Used for Progression Visualization
The system SHALL use an appropriate visualization technique for the logarithmic progression curve.

#### Scenario: Chart Renders in BasePage.jsx
- GIVEN the hierarchy section is loaded
- WHEN the chart component renders
- THEN it SHALL use either an SVG path, a canvas element, or a charting library (e.g., recharts, chart.js) to draw the logarithmic curve
- AND the chart SHALL NOT be a static image — it SHALL be dynamically generated from backend data

#### Scenario: Chart Loads Without Blocking Page
- GIVEN the player opens the Base tab
- WHEN the hierarchy data is still loading
- THEN a loading skeleton or spinner SHALL be displayed in place of the chart
- AND the rest of the Base tab SHALL remain interactive during chart load

---

### Requirement: Mobile / Narrow Viewport Support
The system SHALL ensure the hierarchy chart remains readable on narrower viewports.

#### Scenario: Chart Scales on Small Screens
- GIVEN the player views BasePage on a viewport narrower than 768px
- WHEN the hierarchy chart renders
- THEN the chart SHALL scale or reflow to fit without horizontal overflow
- AND axis labels SHALL remain legible (not overlapping or cut off)
