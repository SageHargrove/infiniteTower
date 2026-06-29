# PvP Events Specification

## Purpose
Design a time-limited PvP events system where players compete for exclusive rewards on leaderboards, inspired by competitive arcs in manhwa like "Pick Me Up" — to be fully specced now and implemented as a later-stage feature.

## Context
- No PvP event backend router currently exists; a new one will need to be created (e.g., `backend/routers/pvp_events.py`)
- No PvP event frontend page currently exists; a new one will be needed (e.g., `frontend/src/pages/PvPEventsPage.jsx`)
- Leaderboard eligibility is gated by the difficulty setting (see: difficulty-settings spec)
- This feature is intentionally specced in advance — implementation should not begin until core game loop is stable
- Events are analogous to "ranked seasons" in mobile gacha games (e.g., Arknights, Blue Archive, Limbus Company)
- The flagship event type is "Battle for the Tower Floor" — compete to push the highest floor in the event window

## Requirements

### Requirement: Event Definition and Configuration
The system SHALL allow administrators to define time-limited PvP events with configurable parameters.

#### Scenario: Admin Creates a PvP Event
- GIVEN an admin accesses the event management interface (backend admin route or CLI)
- WHEN they create a new event
- THEN the event record SHALL include:
  - `event_id`: unique identifier
  - `event_type`: e.g., `"floor_race"`, `"boss_kill"`, `"cumulative_score"`
  - `name`: display name (e.g., "Battle for the Tower — Season 3")
  - `start_time`: UTC datetime
  - `end_time`: UTC datetime
  - `eligible_difficulties`: list (e.g., `["normal", "hard"]`)
  - `reward_tiers`: array of ranked reward brackets
  - `leaderboard_size`: max visible rankings
- AND the event SHALL become active when `current_time >= start_time`

#### Scenario: Event Becomes Active
- GIVEN an event's `start_time` has been reached
- WHEN a player loads the PvP Events page
- THEN the event SHALL appear as "Active" with a countdown to `end_time`
- AND the player SHALL be able to submit scores/progress to this event

#### Scenario: Event Expires
- GIVEN an event's `end_time` has passed
- WHEN any player views the event
- THEN the event status SHALL change to "Ended"
- AND final leaderboard rankings SHALL be frozen
- AND rewards SHALL be distributed to eligible players

---

### Requirement: Floor Race Event Type — "Battle for the Tower Floor"
The system SHALL support a "floor race" event type where players compete to reach the highest floor within the event window.

#### Scenario: Player Submits Floor Clear During Active Event
- GIVEN a "floor_race" event is active
- AND the player's profile difficulty is eligible for the event
- WHEN the player successfully clears a floor during the event window
- THEN the event backend SHALL record their highest cleared floor for this event
- AND if this floor is higher than their previous submission, it SHALL replace it
- AND the leaderboard SHALL update with the new standing

#### Scenario: Tiebreaker by Time
- GIVEN two players have cleared the same highest floor
- WHEN leaderboard rankings are computed
- THEN the player who cleared that floor in less total time SHALL be ranked higher
- AND time SHALL be measured as the duration of the floor battle, not real-world time elapsed since event start

#### Scenario: Player Views Their Standing
- GIVEN an active floor race event
- WHEN a player opens the event leaderboard
- THEN they SHALL see:
  - Their current rank
  - Their highest floor cleared in the event
  - Their tiebreaker time
  - Top N players' standings (configurable, e.g., top 100)
  - Their reward tier preview based on current rank

---

### Requirement: Difficulty-Segregated Leaderboards
The system SHALL separate or handicap leaderboards by difficulty to ensure fair competition.

#### Scenario: Hard Mode Players Compete in Separate Tier
- GIVEN an event with `eligible_difficulties: ["normal", "hard"]`
- WHEN the leaderboard is rendered
- THEN Hard mode rankings SHALL be displayed in a separate "Hard Mode" leaderboard tier
- AND Normal mode players SHALL compete only against other Normal mode players
- AND Hard mode tiers SHALL offer superior rewards (exclusive heroes, higher gem payouts)

#### Scenario: Easy Mode Profiles Are Excluded
- GIVEN an event is active
- WHEN a player with `difficulty: "easy"` opens the PvP Events page
- THEN the event SHALL display as "Not Eligible — Easy Mode"
- AND they SHALL NOT be able to submit scores or appear on any leaderboard

---

### Requirement: Reward Tiers
The system SHALL distribute rewards at event end based on final leaderboard rank.

#### Scenario: Tiered Reward Structure Defined
- GIVEN an event is configured with reward tiers
- THEN reward tiers SHALL be defined as rank brackets (e.g., Rank 1, Ranks 2–5, Ranks 6–20, Ranks 21–100, Participation)
- AND each tier SHALL specify: gem amount, gold amount, optional exclusive hero token, optional exclusive title

#### Scenario: Exclusive Rewards for Top Tier
- GIVEN a player finishes in Rank 1 of their difficulty tier
- WHEN the event ends and rewards are distributed
- THEN they SHALL receive a unique, event-exclusive hero summon token (obtainable only via this event ranking)
- AND the hero from this token SHALL be marked as "Event-Exclusive" in their roster

#### Scenario: Participation Reward for All Eligible Players
- GIVEN a player participated in the event (submitted at least one score)
- WHEN the event ends
- THEN they SHALL receive the participation reward regardless of final rank
- AND participation rewards SHALL be modest (e.g., 50 gems, 5,000 gold) to incentivize engagement without trivializing top rewards

---

### Requirement: Event Notification and UI
The system SHALL notify players of active and upcoming events.

#### Scenario: Event Banner on Home Screen
- GIVEN an event is active or starts within 24 hours
- WHEN the player loads the main screen
- THEN a prominent event banner SHALL be displayed (e.g., a pulsing card or notification badge)
- AND clicking the banner SHALL navigate to the PvP Events page

#### Scenario: Countdown Timer on Event Page
- GIVEN the player opens an active event in `PvPEventsPage.jsx`
- WHEN the page renders
- THEN a live countdown timer SHALL display the time remaining until the event ends
- AND the timer SHALL update in real-time (client-side countdown from server-provided end_time)

#### Scenario: Event History Tab
- GIVEN a player navigates to the PvP Events page
- WHEN past events exist
- THEN a "Past Events" section or tab SHALL display completed events with final standings and distributed rewards
- AND players SHALL be able to verify their rewards were received

---

### Requirement: Anti-Exploit Measures
The system SHALL include safeguards against score manipulation.

#### Scenario: Score Submitted Only After Verified Battle Completion
- GIVEN a floor race event is active
- WHEN a player's battle concludes
- THEN the floor clear SHALL only be counted if the backend has independently verified the battle result (not trusting client-side data)
- AND floors cleared outside the event window (before start or after end) SHALL NOT be counted

#### Scenario: Duplicate Event Entry Prevented
- GIVEN a player has already submitted a score for this event
- WHEN a subsequent (lower) floor clear occurs
- THEN the leaderboard SHALL retain only the player's personal best, not stack or accumulate scores
