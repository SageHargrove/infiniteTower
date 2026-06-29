# Claude Game Mechanics, Bosses & Story Spec

Please implement the following backend/gameplay mechanic updates in the Python backend:

## 1. Talent Reveal Building
Currently, talent is just a number going up (e.g., 1/1000). We need to replace this with a dedicated building (e.g., "Talent Observatory" or "Potential Appraiser") where heroes are placed to *reveal* their innate talent.
- **Mechanics**: You place a hero in this building, and after a set time (e.g., 5-30 minutes), their talent is revealed. The cost to reveal talent should scale with their Star Level.
- **Levels of Reveal**: 
  - **Level 1**: Reveals a general descriptor (e.g., "Gifted", "Talented").
  - **Level 2**: Reveals a more specific range of their talent.
  - **Level 3**: Reveals their exact talent level/stats.
  *(Note: This is strictly for REVEALING talent, not a training building).*

## 2. Summoning & Pity System
- **Hidden Pity**: The 3-star pity counter is currently visible in the UI. Please hide this entirely (or move it to just the tutorial text). It should be a hidden mechanic so it doesn't look goofy.
- **Spark System Update**: Adjust the spark/pity system so that doing 100 summons guarantees a 4-star hero.

## 3. Enemies and Bosses Updates
- **Art Checks & New Enemies**: Do a pass through current enemies and find any that break the art style. Come up with ideas for new enemies.
- **Raid Bosses**: Reduce the number of Raid Bosses to exactly 2 (Floor 50 and Floor 100).
- **Dragon Boss**: Add a Dragon Boss or elite versions of the current normal dragon enemy.
- **7-Star Boss**: Create a humanoid evil 7-star boss character (e.g., "GR3G The Beast"). Ensure it stands out as an elite threat.

## 4. Combat Mechanics & Bug Fixes
- **Dead Boss Swing Bug**: There is a bug where heroes will continue to swing at a dead boss/mini-boss (like the Goblin King) even after it has died and the level has theoretically finished. Fix combat resolution so attacks stop when the boss dies.
- **Positioning Bug**: Fix the frontliner positioning bug where two frontliners were moving to the back during combat/exploration unexpectedly.
- **Background Tower Combat**: Make tower fights run in the background. If a user switches tabs, the combat should continue simulating/running instead of instantly finishing or freezing.

## 5. Story and Floor Variety
- **Story Promos**: In stories, text should unlock sentence-by-sentence (after ending punctuation) rather than unlocking mid-sentence.
- **Lore Pages**: Add a "Lore Readout" page before the 10th floor, and periodically add new lore pages as the player progresses higher.
- **Floor Variety**: Currently, floors are just basic combat. After every 10 floors, introduce variety such as:
  - Exploration events
  - Field combat / War
  - Find and retrieve missions
  - Escort missions
- **Deterministic Floors**: Floors do NOT change on subsequent runs or retries. Floor 1 is always the exact same Floor 1 with the same enemies and same events for every player/run. The layout and content of a floor must be deterministic.
