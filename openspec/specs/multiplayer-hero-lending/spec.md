# Multiplayer Hero Lending Specification

## Purpose
Design a social multiplayer feature where players can lend heroes to friends' bases for stat training purposes — enabling a training market economy without compromising the uniqueness of each player's floor-clearing roster.

## Context
- This is a future multiplayer/social feature; no multiplayer infrastructure currently exists in the codebase
- The feature requires new backend endpoints and models, and a new frontend UI section
- Key design constraint: lent heroes CANNOT be used for floor clearing at the borrowing base — they are training-only
- This preserves the integrity of the "your tower, your heroes" progression system
- Inspired by friend-support mechanics in games like Fate/Grand Order, AFK Arena's borrowing system, and training loan systems in sports management games
- The training market becomes a passive income stream for players with strong benched heroes

## Requirements

### Requirement: Hero Lending from Lender's Perspective
The system SHALL allow a player to lend a hero to a friend's base for training purposes.

#### Scenario: Player Lists Hero for Lending
- GIVEN a player has a hero not currently on their active floor-clearing team
- WHEN they navigate to the Hero Lending section
- THEN they SHALL be able to select an eligible hero and mark it as "Available for Lending"
- AND they SHALL be able to specify:
  - A daily gem/gold fee for training access
  - A maximum lending duration (e.g., 1–7 days)
  - Specific training types they allow (optional, e.g., "strength training only")
- AND the hero SHALL remain visible in the lender's roster as "On Loan" during the lending period

#### Scenario: Hero Cannot Be on Both Lending and Active Team
- GIVEN a player has marked a hero as available for lending
- WHEN they attempt to add that same hero to their active floor team
- THEN the system SHALL prevent this action
- AND a message SHALL appear: "This hero is currently listed for lending. Remove from lending to use in your team."

#### Scenario: Lender Receives Compensation
- GIVEN a borrower has rented the lender's hero for a training session
- WHEN the training session completes
- THEN the lender SHALL automatically receive the agreed gems/gold fee
- AND a notification SHALL appear for the lender: "[Hero Name] completed training at [Friend]'s base — you earned X gems"

#### Scenario: Lender Can Recall Hero Early
- GIVEN a lender's hero is currently on loan
- WHEN the lender requests early recall
- THEN the hero SHALL be returned at the end of the current active training session (not mid-session)
- AND the borrower SHALL be notified: "[Hero Name] has been recalled by their master"
- AND a partial fee proportional to time served SHALL be paid to the lender

---

### Requirement: Hero Borrowing from Borrower's Perspective
The system SHALL allow a player to borrow a friend's (or market) hero for training at their own base facilities.

#### Scenario: Player Browses Training Market
- GIVEN a player opens the Training Market section
- WHEN the market loads
- THEN they SHALL see available heroes listed for lending from:
  1. Their friend list (prioritized)
  2. A wider matchmade pool (players with similar game progression)
- AND each listing SHALL display: hero name, class, rarity, key stats, daily training fee, available duration

#### Scenario: Player Rents a Hero for Training
- GIVEN a player selects a hero from the Training Market
- WHEN they confirm the rental (paying the agreed fee in gems/gold)
- THEN the borrowed hero SHALL appear in the borrower's base as a "Guest Hero"
- AND the Guest Hero SHALL be assignable to training facilities only (Training Grounds, Library, etc.)
- AND the Guest Hero SHALL NOT appear in the borrower's floor team selection

#### Scenario: Borrowed Hero Provides Training Bonuses
- GIVEN a Guest Hero is assigned to the borrower's Training Grounds
- WHEN a training session runs
- THEN the player's own heroes training alongside the Guest Hero SHALL receive a bonus XP or stat gain based on the Guest Hero's power level
- AND a stronger (higher rarity/level) Guest Hero SHALL provide a larger training bonus

#### Scenario: Specific Skill Training via Gems
- GIVEN a Guest Hero is assigned to a training facility
- WHEN the borrower pays an additional gems fee for targeted skill training
- THEN a specific stat or skill (e.g., "Sword Mastery", "Strength", "Mana Efficiency") SHALL be trained at an accelerated rate
- AND the available skill types SHALL be based on the Guest Hero's class specialization

---

### Requirement: Guest Hero Restrictions (Core Design Constraint)
The system SHALL strictly enforce that Guest Heroes cannot be used for floor clearing.

#### Scenario: Guest Hero Not Available for Floor Teams
- GIVEN a player has a Guest Hero at their base
- WHEN they open the Team Composition screen for floor challenge
- THEN the Guest Hero SHALL NOT appear in the selectable hero pool
- AND no UI element SHALL suggest or allow adding a Guest Hero to a floor team

#### Scenario: Guest Hero Returns After Lending Duration Expires
- GIVEN a lending arrangement has reached its agreed `max_duration`
- WHEN the expiry time is reached
- THEN the Guest Hero SHALL automatically return to the lender's roster
- AND any ongoing training session SHALL be immediately completed (prorated rewards granted)
- AND both parties SHALL receive a notification of the return

---

### Requirement: Training Market Economy
The system SHALL maintain a balanced economy for the Training Market to prevent exploitation.

#### Scenario: Daily Lending Fee Bounded by System Limits
- GIVEN a player is listing a hero for lending
- WHEN they set a daily fee
- THEN the fee SHALL be capped by the system (e.g., max 500 gems/day for 7★, scaled by rarity tier)
- AND minimum fee SHALL be 1 gem or 100 gold to prevent zero-cost exploits

#### Scenario: Market Supply Gated by Hero Power Tiers
- GIVEN the Training Market listing
- WHEN a player with early-game progression browses the market
- THEN they SHALL primarily see heroes appropriate to their level (power-matched pool)
- AND legendary (6★–7★) heroes SHALL only appear for borrowers whose base is above a certain progression threshold

#### Scenario: Strong Heroes Appear in Training Market Automatically
- GIVEN a player has a hero that exceeds a community power threshold (e.g., top 10% of heroes at that rarity)
- WHEN the player lists the hero for lending
- THEN the hero SHALL be automatically highlighted as "Featured" in the Training Market
- AND featured heroes SHALL attract higher traffic and command premium fees

---

### Requirement: Social Friend List Integration
The system SHALL integrate the lending feature with a player friend/social system.

#### Scenario: Player Adds Friend by Profile ID or Code
- GIVEN a multiplayer social system exists (or is being created alongside this feature)
- WHEN a player adds another player as a friend
- THEN that friend's lent heroes SHALL appear in the "Friends" section of the Training Market (prioritized over strangers)

#### Scenario: Friend Notification When Hero Available
- GIVEN Player A has a hero available for lending
- WHEN a friend (Player B) logs in
- THEN Player B SHALL see a notification or badge on the Training Market indicating a friend has heroes available
- AND they SHOULD be able to go directly to Player A's listed heroes

---

### Requirement: Backend Data Model
The system SHALL define a clear data model for lending arrangements.

#### Scenario: Lending Record Schema
- GIVEN a lending arrangement is created
- THEN the backend SHALL store a lending record containing:
  - `lending_id`: unique ID
  - `lender_profile_id`: the owner's profile
  - `borrower_profile_id`: the renting profile
  - `hero_id`: the specific hero being lent
  - `start_time`: when lending began
  - `end_time`: agreed expiry
  - `daily_fee`: fee per day
  - `allowed_facilities`: list of permitted facility types
  - `status`: `"active"`, `"recalled"`, `"expired"`

#### Scenario: Lending Records Archived After Completion
- GIVEN a lending arrangement ends (expiry, recall, or mutual release)
- WHEN the record is closed
- THEN it SHALL be archived (not deleted) for audit and dispute resolution purposes
- AND summary data (total fee earned, training hours provided) SHALL be added to the lender's profile stats
