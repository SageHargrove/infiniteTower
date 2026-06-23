import React, { useState } from 'react'
import { evolveHero } from '../api/client'
import { ClassBadge } from './HeroCard'

const CLASS_LORE = {
  // Support Base Classes
  "Farmer": { desc: "Tends to the crops, providing steady supplies for the base.", team: "Non-combatant. Keep in the Farm." },
  "Master Farmer": { desc: "An expert in agriculture. Harvests bountiful crops with unmatched efficiency.", team: "Non-combatant. Keep in the Farm." },
  "Harvest Lord": { desc: "Commands the very earth to yield its fruits. The pinnacle of agriculture.", team: "Non-combatant. Keep in the Farm." },
  "Nature's Chosen": { desc: "One with the flora. Plants grow instantly at their touch.", team: "Non-combatant. Keep in the Farm." },
  "Beast Tamer": { desc: "Tames wild beasts to plow fields rapidly, but can also bring them to battle.", team: "Hybrid. Generates supplies, or fights alongside a summoned beast." },
  "Apex Predator": { desc: "Commands the most terrifying monsters of the tower.", team: "Combat Summoner. Overwhelms enemies with beastly companions." },
  "Wild Master": { desc: "A harmonious bond with nature allows for incredible utility and damage.", team: "Hybrid Support/DPS." },
  "Merchant": { desc: "A shrewd trader who generates gold for the base.", team: "Non-combatant. Keep in the Market." },
  "Trade Baron": { desc: "Commands trade routes, multiplying gold income.", team: "Non-combatant. Keep in the Market." },
  "Guild Master": { desc: "Controls the entire market economy.", team: "Non-combatant. Keep in the Market." },
  "Black Market Dealer": { desc: "Deals in shady goods for massive profits.", team: "Non-combatant. Keep in the Market." },

  // Base Combat Classes
  "Warrior": { desc: "A balanced front-line fighter with a sword and shield.", team: "Versatile tank or bruiser." },
  "Spearman": { desc: "Utilizes reach to pierce armor from behind the vanguard.", team: "Mid-line physical DPS." },
  "Thief": { desc: "Nimble and stealthy, excelling in critical strikes and dodging.", team: "Flanking burst physical DPS." },
  "Archer": { desc: "Rains arrows from afar, picking off vulnerable targets.", team: "Back-line consistent physical DPS." },
  "Mage": { desc: "Wields raw arcane energy to devastate groups of enemies.", team: "Back-line AoE magic DPS." },
  "Magic Engineer": { desc: "Blends technology with magic to create deadly turrets and gadgets.", team: "Utility DPS and area control." },
  "Chef": { desc: "Cooks hearty meals that buff allies mid-battle.", team: "Buffing Support." },
  "Medic": { desc: "Heals wounds and keeps the team alive in dire situations.", team: "Primary Healer." },
  "Scout": { desc: "Reveals enemy weaknesses and initiates combat.", team: "Debuffing Support / Initiator." },
  "Quartermaster": { desc: "Manages equipment and supplies, buffing team endurance.", team: "Sustained Buffing Support." },
  "Tactician": { desc: "Analyzes the battlefield, manipulating turn order and granting buffs.", team: "Control and Utility Support." },
  "Priest": { desc: "Channels divine energy to heal and protect allies from dark magic.", team: "Healer and Magic Tank." },
  "Alchemist": { desc: "Throws explosive potions and applies lingering debuffs.", team: "AoE Debuffer and Magic DPS." },
  "Classless": { desc: "A blank slate, waiting to find their true calling.", team: "Weak. Evolve ASAP." },

  // Evolution Tier 1 (Level 30)
  "Knight": { desc: "A heavily armored defender, swearing an oath to protect.", team: "Primary Tank. Taunts enemies and absorbs damage." },
  "Berserker": { desc: "A raging warrior who trades intelligence for raw, bloody power.", team: "Front-line burst DPS. High risk, high reward." },
  "Halberdier": { desc: "Masters the halberd, striking multiple foes in a sweeping arc.", team: "Front-line AoE physical DPS." },
  "Dragoon": { desc: "Leaps high into the air, crashing down with immense force.", team: "Burst DPS with mobility and evasion." },
  "Assassin": { desc: "Strikes from the shadows, executing low-health targets instantly.", team: "Single-target executioner." },
  "Rogue": { desc: "Fights dirty, stealing items and crippling enemies.", team: "Utility DPS / Debuffer." },
  "Sniper": { desc: "Patient and deadly. Capable of ignoring enemy armor.", team: "Long-range armor-piercing DPS." },
  "Ranger": { desc: "A master of the wilds, shooting multiple arrows and setting traps.", team: "Consistent AoE physical DPS." },
  "Sorcerer": { desc: "Specializes in pure, unbridled destruction.", team: "Glass cannon magic DPS." },
  "Spellblade": { desc: "Imbues their weapon with magic, fighting in the fray.", team: "Hybrid melee/magic DPS." },
  "Gunner": { desc: "Wields experimental firearms for massive burst damage.", team: "High burst, long reload DPS." },
  "Mechanic": { desc: "Builds advanced autonomous drones to fight for them.", team: "Summoner / Sustained DPS." },
  "Culinary Master": { desc: "Their meals grant permanent buffs for the duration of the tower run.", team: "Scaling Buffer." },
  "Battle Medic": { desc: "Heals while simultaneously dealing damage with toxins.", team: "Hybrid Healer/DPS." },
  "Surgeon": { desc: "Can revive fallen allies and heal critical wounds.", team: "Burst Healer and Resurrector." },
  "Pathfinder": { desc: "Never gets lost, revealing hidden paths and treasures.", team: "Exploration Utility." },
  "Spy": { desc: "Infiltrates enemy lines, disabling traps and confusing foes.", team: "Saboteur / Debuffer." },
  "Commander": { desc: "Leads from the front, their presence inspiring the entire team.", team: "Aura Buffer and Tank." },
  "Strategist": { desc: "Anticipates enemy moves, providing massive defensive buffs.", team: "Defensive Utility." },
  "Cleric": { desc: "A bastion of holy light, cleansing debuffs and healing.", team: "Cleanser and Healer." },
  "Paladin": { desc: "A holy warrior who smites evil and shields the weak.", team: "Hybrid Tank/Healer." },
  "Master Alchemist": { desc: "Brews legendary concoctions that completely alter the battlefield.", team: "AoE Controller." },
  "Poisoner": { desc: "Coats everything in deadly toxins that drain life over time.", team: "DoT Magic DPS." },

  // Evolution Tier 2 (Level 60)
  "Holy Knight": { desc: "Imbued with divine power, completely immune to dark magic.", team: "Ultimate Magic Tank." },
  "Dark Knight": { desc: "Sacrifices their own life force to deal apocalyptic damage.", team: "Self-damaging Burst DPS." },
  "Bloodrager": { desc: "A whirlwind of death. Heals based on damage dealt.", team: "Sustained lifesteal DPS." },
  "Juggernaut": { desc: "An unstoppable force of muscle and rage. Cannot be crowd-controlled.", team: "Unstoppable front-line terror." },
  "Royal Guard": { desc: "The ultimate protector. Takes damage in place of allies.", team: "Ultimate Physical Tank." },
  "Valkyrie": { desc: "A celestial warrior who descends from the heavens to smite foes.", team: "Holy Physical DPS." },
  "Dragon Knight": { desc: "Commands the power of dragons, breathing fire and shattering armor.", team: "AoE Bruiser." },
  "Shadow Dancer": { desc: "Moves between dimensions, striking before the enemy can react.", team: "Evasive Burst DPS." },
  "Nightshade": { desc: "A master of lethal poisons and unseen strikes.", team: "Executioner and DoT." },
  "Phantom": { desc: "Leaves illusions to confuse enemies while dealing massive damage.", team: "Evasive Utility DPS." },
  "Sharpshooter": { desc: "Never misses. Every shot is a guaranteed critical hit.", team: "Ultimate Single-Target Physical DPS." },
  "Beastmaster": { desc: "Fights alongside legendary spirit beasts.", team: "Summoner / Physical DPS." },
  "Archmage": { desc: "Master of all elements. Can cast multiple spells at once.", team: "Ultimate AoE Magic DPS." },
  "Necromancer": { desc: "Raises fallen enemies to fight for the team.", team: "Summoner / Debuffer." },
  "Arcane Knight": { desc: "A perfect blend of magic and martial prowess.", team: "Ultimate Hybrid DPS." },
  "Artillery Commander": { desc: "Calls down massive orbital strikes.", team: "Screen-clearing Burst DPS." },
  "Ironclad": { desc: "Pilots a massive mechanical suit of armor.", team: "Ranged Tank / Bruiser." },
  "Grandmaster Chef": { desc: "Their food makes the team practically immortal.", team: "Ultimate Buffer." },
  "Miracle Worker": { desc: "Can fully heal the entire team and resurrect multiple allies.", team: "Ultimate Healer." },
  "Plague Doctor": { desc: "Spreads deadly diseases that wipe out enemy ranks.", team: "Ultimate DoT DPS." },
  "Grand Strategist": { desc: "Dictates the flow of battle. Grants allies extra turns.", team: "Ultimate Utility." },
  "Warlord": { desc: "Their battle cries grant immense power and lifesteal.", team: "Aggressive Aura Buffer." },
  "High Priest": { desc: "Channels the power of the gods, granting invulnerability.", team: "Ultimate Defensive Support." },
  "Inquisitor": { desc: "Hunts down magic users, purging buffs and dealing holy damage.", team: "Anti-Magic DPS." },
  "Grand Alchemist": { desc: "Transmutes the battlefield, turning enemy armor to dust.", team: "Ultimate Debuffer." }
};

export default function ClassEvolutionModal({ hero, onClose, onEvolve }) {
  const [selectedClass, setSelectedClass] = useState(null);
  const [evolving, setEvolving] = useState(false);

  if (!hero || !hero.evolution_options) return null;

  const handleConfirm = async () => {
    if (!selectedClass) return;
    setEvolving(true);
    try {
      const result = await evolveHero(hero.id, selectedClass);
      onEvolve(result.new_class);
      onClose();
    } catch (e) {
      alert(e.message || "Failed to evolve.");
    } finally {
      setEvolving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.85)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      backdropFilter: 'blur(5px)'
    }}>
      <div className="card" style={{ 
        width: '90%', maxWidth: '900px', maxHeight: '90vh', overflowY: 'auto',
        padding: '2rem', display: 'flex', flexDirection: 'column', gap: '2rem',
        border: '1px solid var(--purple)', boxShadow: '0 0 30px rgba(157, 78, 221, 0.4)'
      }}>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontFamily: 'Cinzel, serif', fontSize: '2.5rem', color: 'var(--text-hi)' }}>
              Class Advancement
            </div>
            <div className="text-dim" style={{ fontSize: '1.2rem', marginTop: '0.5rem' }}>
              {hero.name} has reached Level {hero.level} and is ready to evolve.
            </div>
          </div>
          <button className="btn" onClick={onClose} style={{ fontSize: '1.5rem', padding: '0.2rem 0.8rem' }}>&times;</button>
        </div>

        <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', minWidth: '200px' }}>
            <img 
              src={`http://localhost:8000/${hero.portrait_path}`} 
              alt={hero.name} 
              style={{ width: '150px', height: '150px', borderRadius: '50%', objectFit: 'cover', objectPosition: 'center 15%', border: '3px solid var(--border)' }}
            />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.5rem', color: 'var(--text-hi)' }}>{hero.name}</div>
              <div style={{ marginTop: '0.5rem' }}><ClassBadge heroClass={hero.hero_class} /></div>
            </div>
          </div>

          <div style={{ color: 'var(--purple)', fontSize: '2rem' }}>➞</div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="text-dim" style={{ fontFamily: 'Cinzel, serif', fontSize: '1.2rem', marginBottom: '0.5rem' }}>
              Choose a New Path:
            </div>
            {hero.evolution_options.map(evoClass => {
              const lore = CLASS_LORE[evoClass] || { desc: "A mysterious path of power.", team: "Unknown." };
              const isSelected = selectedClass === evoClass;
              return (
                <div 
                  key={evoClass}
                  onClick={() => setSelectedClass(evoClass)}
                  style={{
                    padding: '1.5rem',
                    border: isSelected ? '2px solid var(--gold)' : '1px solid var(--border)',
                    background: isSelected ? 'rgba(201, 168, 76, 0.1)' : 'rgba(255,255,255,0.03)',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: isSelected ? '0 0 15px rgba(201,168,76,0.3)' : 'none'
                  }}
                >
                  <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.6rem', color: isSelected ? 'var(--gold)' : 'var(--text-hi)', marginBottom: '0.5rem' }}>
                    {evoClass}
                  </div>
                  <div className="text-dim" style={{ fontSize: '1rem', lineHeight: 1.5, fontStyle: 'italic', marginBottom: '0.8rem' }}>
                    "{lore.desc}"
                  </div>
                  <div style={{ fontSize: '0.9rem', color: '#a8c830' }}>
                    <span style={{ fontWeight: 'bold' }}>Team Fit:</span> {lore.team}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem', borderTop: '1px solid var(--border)', paddingTop: '2rem' }}>
          <button 
            className="btn btn-gold" 
            disabled={!selectedClass || evolving}
            onClick={handleConfirm}
            style={{ fontSize: '1.4rem', padding: '1rem 3rem' }}
          >
            {evolving ? 'Evolving...' : selectedClass ? `Confirm Evolution: ${selectedClass}` : 'Select a Path'}
          </button>
        </div>

      </div>
    </div>
  );
}
