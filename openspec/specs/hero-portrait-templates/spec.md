# Hero Portrait Templates Specification

## Purpose
Overhaul the hero card portrait template visual style to reflect rarity through border color, star iconography, and a dark cinematic aesthetic inspired by the "Islat Han" card style.

## Context
- Hero card images are generated in `backend/services/card_template_service.py`
- Card regeneration is triggered via `backend/regen_cards.py`
- Current borders do not reflect rarity; star count is not visually displayed on the card
- Heroes have rarity tiers from 1★ to 7★, with the gap between 5★/6★/7★ representing legendary/unique power
- The visual gap between tiers must feel meaningful — 5★+ should look dramatically different from 1–4★

## Requirements

### Requirement: Rarity-Based Border Colors
The system SHALL render each hero card border in a color that corresponds to the hero's star rarity tier.

#### Scenario: 1★ Hero Card Rendered
- GIVEN a hero with `star_rating == 1`
- WHEN `card_template_service.py` generates the card image
- THEN the card border SHALL be rendered in iron grey (e.g., `#8a8a8a` or a brushed-steel gradient)
- AND the border weight SHALL be thin and understated

#### Scenario: 2★ Hero Card Rendered
- GIVEN a hero with `star_rating == 2`
- WHEN the card image is generated
- THEN the card border SHALL be rendered in bronze (e.g., `#cd7f32` warm metallic tone)

#### Scenario: 3★ Hero Card Rendered
- GIVEN a hero with `star_rating == 3`
- WHEN the card image is generated
- THEN the card border SHALL be rendered in silver (e.g., `#c0c0c0` cool silver gradient)

#### Scenario: 4★ Hero Card Rendered
- GIVEN a hero with `star_rating == 4`
- WHEN the card image is generated
- THEN the card border SHALL be rendered in gold (e.g., `#ffd700` warm gold with slight glow)

#### Scenario: 5★ Hero Card Rendered
- GIVEN a hero with `star_rating == 5`
- WHEN the card image is generated
- THEN the card border SHALL be rendered in deep amethyst purple (e.g., `#9b30ff`)
- AND the border SHALL have a subtle luminous glow effect to differentiate from 4★

#### Scenario: 6★ Hero Card Rendered
- GIVEN a hero with `star_rating == 6`
- WHEN the card image is generated
- THEN the card border SHALL use a unique ornate design — e.g., rune-etched dark gold or obsidian-and-crimson
- AND the border design SHALL be visually distinct from all other tiers (not just a color swap)
- AND an optional subtle animated shimmer effect SHOULD be supported for future use

#### Scenario: 7★ Hero Card Rendered
- GIVEN a hero with `star_rating == 7`
- WHEN the card image is generated
- THEN the card border SHALL render a prismatic / rainbow holographic effect cycling through hues
- AND the visual weight and complexity of the border SHALL far exceed all lower tiers
- AND a "prismatic" label or glyph SHOULD appear in the corner of the card

---

### Requirement: Star Icons Displayed on Card
The system SHALL display star icons on the hero card corresponding to the hero's star rating.

#### Scenario: Stars Positioned at Top of Card
- GIVEN any hero card being generated
- WHEN the card template is applied
- THEN star icons SHALL be rendered in the upper region of the card (above the portrait art)
- AND the number of star icons SHALL exactly match `hero.star_rating`
- AND stars SHALL be visually filled/colored according to the rarity tier color

#### Scenario: Hero Name at Bottom of Card
- GIVEN any hero card being generated
- WHEN the card template is applied
- THEN the hero's name SHALL appear at the bottom of the card
- AND the name text SHALL use a dark cinematic font (e.g., serif or stylized sans)
- AND the name area SHALL contrast clearly against the portrait background (dark banner or semi-transparent overlay)

#### Scenario: Star Count at Top of Card
- GIVEN any hero card being generated
- WHEN the card template is applied
- THEN the star rating SHALL be shown at the top of the card via `N★` notation alongside the star icons
- AND the star count label SHALL NOT overlap the portrait face/body

---

### Requirement: Islat Han Dark Cinematic Aesthetic
The system SHALL apply a dark, dramatic cinematic aesthetic to all hero cards reminiscent of the "Islat Han" art style.

#### Scenario: Card Background Style Applied
- GIVEN a hero card being rendered
- WHEN the template overlays are applied
- THEN the card background shall use a dark vignette (dark edges, lighter center) to draw focus to the hero portrait
- AND the card color palette SHALL lean dark (near-black, deep navy, or shadow tones) outside the portrait region
- AND class or faction iconography SHOULD appear subtly in the card background

#### Scenario: Rarity Visual Gap — Low Tiers (1★–2★ and 3★–4★)
- GIVEN heroes of tier 1★ vs 2★, or 3★ vs 4★
- WHEN their cards are displayed side by side
- THEN the visual difference SHALL be noticeable but modest (primarily border color shift)
- AND no glow or shimmer effects SHALL be applied to 1–4★ cards

#### Scenario: Rarity Visual Gap — High Tiers (5★–7★)
- GIVEN heroes of tier 5★, 6★, and 7★
- WHEN their cards are displayed side by side
- THEN each tier SHALL look dramatically more impressive than the previous
- AND the gap between 4★ and 5★ SHALL feel like a qualitative leap (not just a color change)
- AND 7★ cards SHALL immediately read as uniquely powerful even at a glance

---

### Requirement: Fallback Tier Names
The system SHALL support fallback tier name labels if border colors alone are insufficient for clarity.

#### Scenario: Tier Name Label Applied
- GIVEN a card where the rarity color alone may be ambiguous (e.g., in low-contrast display)
- WHEN the card is rendered
- THEN a small tier name badge SHALL be optionally rendered (e.g., "Bronze", "Silver", "Gold", "Prismatic")
- AND the badge SHALL not obscure the hero's face or name
- AND the badge SHALL use tier-appropriate styling (color, font weight)

---

### Requirement: Bulk Regeneration via regen_cards.py
The system SHALL allow bulk card image regeneration after template changes.

#### Scenario: All Cards Regenerated
- GIVEN updated border/star logic in `card_template_service.py`
- WHEN `python backend/regen_cards.py` is executed
- THEN all existing hero card images SHALL be regenerated using the new template
- AND any missing cards SHALL be created
- AND success/failure counts SHALL be logged to stdout
