# Item Auto-Equip Fix Specification

## Purpose
Remove or improve the handling of lowest-tier (F-grade or equivalent) weapons in the inventory UI, which currently appear as clutter due to being auto-equipped placeholder items with poor-quality visuals.

## Context
- Item/inventory display pages are in `frontend/src/pages/` (look for inventory or items-related pages)
- Backend items router is in `backend/routers/` (items or equipment router)
- Current behavior: the lowest tier weapons (grade F or equivalent) are automatically equipped to new heroes and appear in the inventory list alongside manually obtained items
- These placeholder items have no user-selected artwork, making the inventory look unpolished
- Two valid resolution paths exist:
  1. **Hide them**: Auto-equipped items are invisible in inventory UI (they exist but are transparent to the player)
  2. **Beautify them**: Give them generated artwork so they look intentional and part of the game world
- This spec covers both options so the implementer can choose

## Requirements

### Requirement: Option A — Hide Auto-Equipped Base Items from Inventory
The system SHALL provide a mode where lowest-tier (auto-equipped) items are hidden from the inventory display.

#### Scenario: F-Grade Items Not Shown in Inventory List
- GIVEN a player opens the inventory page
- WHEN the item list renders
- THEN items with grade `"F"` that are flagged as `auto_equipped: true` SHALL NOT appear in the item list
- AND the item count displayed (e.g., "Showing 12 items") SHALL exclude these hidden items
- AND the items SHALL still be functionally equipped to heroes (hidden ≠ unequipped)

#### Scenario: Hero Equipment Panel Still Shows Auto-Equipped Items
- GIVEN F-grade auto-equipped items are hidden from the main inventory
- WHEN the player views a specific hero's equipment panel
- THEN the hero's equipped items (including F-grade) SHALL be visible in that hero's equipment slots
- AND a label or icon SHALL indicate the item is "Auto-Equipped" (to explain why they didn't pick it)

#### Scenario: Player Can Toggle Visibility of Base Items
- GIVEN F-grade items are hidden by default
- WHEN the player toggles a "Show all items" filter in the inventory UI
- THEN F-grade auto-equipped items SHALL become visible in the list
- AND a banner or label SHALL note: "Lowest-tier auto-equipped items shown — these are equipped by default"

---

### Requirement: Option B — AI-Generated Artwork for F-Grade Items
The system SHALL support assigning generated artwork to F-grade items so they appear intentional and visually cohesive.

#### Scenario: F-Grade Items Display Generated Artwork
- GIVEN F-grade items have been assigned AI-generated artwork (via a generation script or asset pipeline)
- WHEN the inventory renders an F-grade item
- THEN it SHALL display the generated artwork image instead of a placeholder or broken image
- AND the artwork SHALL be stylistically consistent with the game's dark fantasy aesthetic

#### Scenario: Generated Artwork Stored and Served Correctly
- GIVEN artwork has been generated for F-grade weapon types
- WHEN the frontend fetches an item's image
- THEN the image SHALL be served from the same asset endpoint used for higher-grade items
- AND no missing image errors or fallback placeholders SHALL appear for F-grade items with generated art

#### Scenario: Artwork Reflects Item Type
- GIVEN an F-grade item of type "Sword"
- WHEN its generated artwork is displayed
- THEN the image SHALL depict a crude or rudimentary sword (visually readable as the item type)
- AND F-grade items SHALL look clearly inferior to B+/A/S-grade items of the same type
- AND the art style SHALL remain dark-fantasy appropriate (not cartoony or out of genre)

---

### Requirement: Backend Grade Filtering Endpoint
The system SHALL provide a backend filter option to exclude lowest-tier items from inventory responses.

#### Scenario: Inventory API Supports Grade Filter
- GIVEN the items/inventory router in `backend/routers/`
- WHEN the frontend requests the player's inventory with `?exclude_grades=F` (or equivalent query parameter)
- THEN the response SHALL exclude all F-grade items
- AND the total item count in the response SHALL reflect only the non-excluded items

#### Scenario: Default API Response Excludes F-Grade (When Option A is Active)
- GIVEN Option A (hide auto-equipped items) is the chosen implementation
- WHEN the frontend fetches inventory without explicit filters
- THEN the backend SHALL omit F-grade auto-equipped items from the default response
- AND `auto_equipped: true` + `grade: "F"` SHALL be the filter criteria

---

### Requirement: Auto-Equip Logic Remains Functional
The system SHALL preserve the auto-equip behavior regardless of whether items are hidden or beautified.

#### Scenario: New Hero Receives Auto-Equipped Items on Creation
- GIVEN a hero is summoned or created
- WHEN the hero is first added to the player's roster
- THEN they SHALL automatically be equipped with the appropriate F-grade starter items for their class
- AND this behavior SHALL occur regardless of whether F-grade items are visible in the inventory UI

#### Scenario: Auto-Equipped Item Cannot Be Sold or Discarded
- GIVEN a hero has an F-grade auto-equipped item
- WHEN a player attempts to sell or discard the item
- THEN the system SHALL prevent the action
- AND a message SHALL explain: "This item is a base equipment and cannot be removed directly. Replace it by equipping a higher-grade item."

#### Scenario: Auto-Equipped Item Replaced When Better Item Equipped
- GIVEN a hero has an F-grade auto-equipped weapon
- WHEN the player equips any higher-grade weapon of the same type to that hero
- THEN the F-grade item SHALL be automatically unequipped
- AND it SHALL either return to inventory (hidden mode) or be permanently discarded (auto-discard mode, configurable)

---

### Requirement: Inventory Visual Quality
The system SHALL ensure the inventory page looks polished regardless of whether F-grade items are hidden or shown.

#### Scenario: Empty Inventory State Does Not Look Broken
- GIVEN all F-grade items are hidden and the player has not yet obtained higher-tier items
- WHEN the inventory page renders
- THEN an intentional empty state message SHALL appear (e.g., "No items yet — visit the Equipment Gacha to obtain gear")
- AND no blank white space or broken layouts SHALL appear

#### Scenario: Item Grade Badge Shown on Each Item
- GIVEN any item is displayed in the inventory
- WHEN it renders
- THEN a grade badge (e.g., "F", "B+", "S") SHALL be visible on or near the item image
- AND the grade badge color SHALL match the equipment grade tier color system (consistent with hero rarity color conventions)
