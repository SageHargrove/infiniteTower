import React, { useState } from 'react'
import { regenerateProfile } from '../api/client'

const MORALE_STATE_LABEL = {
  steady: 'Steady', shaken: 'Shaken', fearful: 'Fearful', broken: 'Broken',
}

// Every base class evolves into a whole tree of named tiers (Warrior →
// Knight/Berserker/Paladin → Aegis/Templar/Bloodrager/... etc — see
// backend services/class_service.py). Hand-mapping ~90 individual evolution
// names to icons/colors is unmaintainable and silently breaks (showing '?')
// every time a new evolution tier gets added. Instead, every evolution name
// is grouped under its base-class family here, and the whole family shares
// one icon + color — new evolutions just need a one-line addition to a list,
// not a whole new icon/color decision.
const CLASS_FAMILIES = {
  'Warrior': { icon: '⚔', color: '#c87830', members: ['Warrior', 'Knight', 'Berserker', 'Paladin', 'Aegis', 'Templar', 'Bloodrager', 'Juggernaut', 'Crusader', 'Divine Sentinel'] },
  'Spearman': { icon: '🔱', color: '#c8a030', members: ['Spearman', 'Lancer', 'Halberdier', 'Dragoon', 'Pikemaster', 'Vanguard', 'Glaive Lord', 'Warlord', 'Wyvern Rider', 'Dragon Knight'] },
  'Thief': { icon: '🗡', color: '#7030c8', members: ['Thief', 'Assassin', 'Rogue', 'Ninja', 'Shadowblade', 'Nightstalker', 'Trickster', 'Shinobi', 'Shadowmaster', 'Infiltrator'] },
  'Archer': { icon: '🏹', color: '#30a030', members: ['Archer', 'Sniper', 'Ranger', 'Crossbowman', 'Marksman', 'Deadeye', 'Beastmaster', 'Warden', 'Arbalist', 'Siege Master'] },
  'Mage': { icon: '🔮', color: '#4060c8', members: ['Mage', 'Sorcerer', 'Warlock', 'Necromancer', 'Summoner', 'Archmage', 'Elementalist', 'Demonologist', 'Voidwalker', 'Lich', 'Deathcaller', 'Grand Summoner', 'Conjurer'] },
  'Spellsword': { icon: '🗲', color: '#5040d0', members: ['Spellsword', 'Eldritch Knight', 'Rune Blade', 'Arcane Lord', 'Mystic Vanguard', 'Rune Master', 'Spellweaver'] },
  'Acolyte': { icon: '☀', color: '#c0c0e0', members: ['Acolyte', 'Cleric', 'Bard', 'Druid', 'Monk', 'High Priest', 'Bishop', 'Maestro', 'Troubadour', 'Archdruid', 'Hierophant', 'Grandmaster', 'Zenith'] },
  'Priest': { icon: '✝', color: '#d8d8f0', members: ['Priest', 'Chaplain', 'Confessor', 'High Confessor', 'Oracle', 'Prophet', 'Saint'] },
  'Tactician': { icon: '♔', color: '#8030c8', members: ['Tactician', 'Strategist', 'Grand Strategist', 'War Master'] },
  'Scout': { icon: '🦅', color: '#a8c830', members: ['Scout', 'Pathfinder', 'Trailblazer', 'Void Walker'] },
  'Blacksmith': { icon: '⚒', color: '#888888', members: ['Blacksmith', 'Master Smith', 'Runesmith', 'Weaponsmith', 'Armorer', 'Artificer', 'Forge Lord'] },
  'Chef': { icon: '🍳', color: '#c85030', members: ['Chef', 'Head Chef', 'Culinary Master', 'Brewmaster', 'Iron Chef', 'Sous Chef', 'Gourmet', 'Master Chef', 'Butcher'] },
  'Medic': { icon: '✚', color: '#30c870', members: ['Medic', 'Field Medic', 'Surgeon', 'Miracle Worker', 'Chief Medical Officer'] },
  'Quartermaster': { icon: '⚖', color: '#c8c030', members: ['Quartermaster', 'Logistics Officer', 'Guild Treasurer', 'Trade Baron', 'Advisor', 'General', 'Commander'] },
  'Farmer': { icon: '🌾', color: '#9aaa30', members: ['Farmer', 'Master Farmer', 'Harvest Lord', 'Beast Tamer', 'Apex Predator', 'Wild Master', 'Forager', 'Scavenger', 'Hoarder', 'Tracker'] },
  'Merchant': { icon: '💰', color: '#d4af37', members: ['Merchant', 'Trader', 'Guild Master', 'Trade Prince', 'Smuggler', 'Black Market Baron', 'Spy', 'Spymaster', 'Tycoon', 'Guildmaster'] },
  'Alchemist': { icon: '⚗', color: '#30c8a0', members: ['Alchemist', 'Master Alchemist', 'Transmuter', 'Philosopher', 'Apothecary', 'Grand Alchemist', 'Herbalist', 'Poisoner', 'Plague Doctor'] },
  'Magic Engineer': { icon: '⚙', color: '#30b8c8', members: ['Magic Engineer'] },
  'Classless': { icon: '✦', color: '#888899', members: ['Classless', 'Adventurer', 'Veteran', 'Mercenary', 'Bounty Hunter', 'Hero', 'Champion'] },
}

const CLASS_ICONS = {}
const CLASS_COLORS = {}
for (const family of Object.values(CLASS_FAMILIES)) {
  for (const name of family.members) {
    CLASS_ICONS[name] = family.icon
    CLASS_COLORS[name] = family.color
  }
}

const SKILL_RARITY_COLORS = {
  common: '#888',
  uncommon: '#4a9a6a',
  rare: '#4a7aaa',
  epic: '#8030c8',
  legendary: '#c9a84c',
}

const APTITUDE_ORDER = ['Combat', 'Survival', 'Tactical', 'Mental', 'Leadership']

function getAptitudeColor(value) {
  if (value >= 90) return '#c9a84c' // gold - exceptional
  if (value >= 75) return '#6fba6f' // green - high
  if (value >= 50) return 'var(--text-hi)' // normal
  if (value >= 25) return '#c87030' // orange - low
  return 'var(--red)' // very low
}

export function Stars({ count, max = 7 }) {
  return (
    <div className={`stars birth-star-${count}`}>
      {Array.from({ length: max }).map((_, i) => (
        <span key={i} className={count === 7 && i < count ? 'rainbow-text' : 'star'}>
          {i < count ? '★' : '☆'}
        </span>
      ))}
    </div>
  )
}

// Keyed by CLASS_FAMILIES name (not individual evolution name) — an
// evolution like Rogue, Paladin, or Adventurer inherits its family's
// tooltip via the same family lookup ClassBadge already does for
// icon/color/archetype below. Per-evolution-name entries previously left
// most of the ~90 evolutions (and, embarrassingly, two base classes that
// had silently-overwritten duplicate keys) falling through to the generic
// "A powerful hero." fallback.
const CLASS_TOOLTIPS = {
  'Warrior': 'A durable frontline fighter that absorbs damage and protects allies.',
  'Spearman': 'A frontline combatant wielding a long-reaching weapon with high pierce damage.',
  'Thief': 'A nimble combatant that strikes from the shadows with high crit chance.',
  'Archer': 'A ranged attacker that rains arrows on the enemy backline.',
  'Mage': 'A spellcaster dealing devastating magical area damage.',
  'Spellsword': 'A hybrid combatant mixing martial prowess with devastating magical strikes.',
  'Acolyte': 'A devout follower providing essential support and minor healing to allies.',
  'Priest': 'Offers divine protection and massive morale recovery.',
  'Tactician': 'A strategic mastermind that provides combat buffs and re-rolls.',
  'Scout': 'Reveals hidden paths and traps, reducing ambush chances.',
  'Blacksmith': 'Upgrades team equipment and provides a baseline stat aura.',
  'Chef': 'Provides powerful morale and Health recovery buffs after combat.',
  'Medic': 'Heals wounds and significantly reduces trauma and stress.',
  'Quartermaster': 'Manages the party inventory, increasing gold and supply gains.',
  'Farmer': 'A hardy worker who increases resource yields and supplies for the team.',
  'Merchant': 'A savvy trader who boosts gold income and finds better deals.',
  'Alchemist': 'Brews potent potions and increases rare material drop rates.',
  'Magic Engineer': 'A master of magical contraptions, building turrets and traps.',
  'Classless': 'A blank slate. Though weak now, it harbors the potential for unique, secret evolutions at higher levels.',
};

const EGO_TOOLTIPS = {
  'Aggressive': 'Desires a team full of damage dealers (Mage, Warrior, etc).',
  'Cautious': 'Desires a team with strong intelligence and healing support.',
  'Tactical': 'Desires a perfectly balanced formation (2 Frontline, 3 Backline).',
  'Leader': 'Desires to be the undisputed leader (highest star rarity on the team).',
  'Lone Wolf': 'Desires a smaller team (3 or fewer heroes) for maximum glory.',
  'Resonant': 'Desires a team composed entirely of the exact same class.'
};

const BATTLE_TENDENCY_TOOLTIPS = {
  'Reckless': 'Fights without caution — as squad Leader, pushes the team to finish off the weakest enemy first. If 1-2★, prone to panicking and fleeing a losing fight.',
  'Calculating': 'Fights with cold precision — as squad Leader, pushes the team to remove the biggest threat first. If 1-2★, may calculate that retreat is the smart play.',
  'Protective': 'Fights to shield others above all else — never breaks and runs, regardless of star.',
  'Glory-Seeking': 'Fights for the kill, not the plan — as squad Leader, pushes the team to finish off the weakest enemy first. Too proud to flee.',
  'Stoic': 'Fights without flair or hesitation, unreadable under pressure — never breaks and runs.',
  'Vengeful': 'Fights like every battle is personal — anger keeps them in the fight, never fleeing.',
};

const FRONTLINE_FAMILIES = ['Warrior', 'Spearman', 'Thief', 'Spellsword', 'Scout', 'Blacksmith', 'Farmer']

export function tierForStar(birthStar) {
  if (birthStar >= 7) return 'prismatic'
  if (birthStar >= 5) return 'gold'
  if (birthStar >= 3) return 'silver'
  return 'bronze'
}

// Status overlay (injured/kia) drawn over the templated card-image background
// (see card_template_service.py — the border/frame itself is now baked into
// that backend-composited image, not drawn here, to avoid a doubled border).
// Reused by both the full HeroCard portrait and the lightweight post-combat
// Team Status summary cards.
export function CardFrame({ birthStar, status, children, style }) {
  const tier = tierForStar(birthStar)
  return (
    <div className={`card-frame card-frame-${tier}`} style={style}>
      {children}
      {status === 'injured' && <div className="card-frame-overlay card-frame-overlay-injured" />}
      {status === 'kia' && (
        <>
          <div className="card-frame-overlay card-frame-overlay-kia" />
          <div className="card-frame-banner">KILLED IN ACTION</div>
        </>
      )}
    </div>
  )
}

export function ClassBadge({ heroClass }) {
  if (!heroClass) return null
  const color = CLASS_COLORS[heroClass] || '#555'
  const icon = CLASS_ICONS[heroClass] || '?'
  
  let familyName = 'Classless'
  for (const [fam, data] of Object.entries(CLASS_FAMILIES)) {
    if (data.members.includes(heroClass)) {
      familyName = fam; break;
    }
  }
  let archetype = 'Backline'
  if (heroClass === 'Classless') archetype = 'Wildcard'
  else if (FRONTLINE_FAMILIES.includes(familyName)) archetype = 'Frontline'

  return (
    <span 
      title={`[${archetype}] ${CLASS_TOOLTIPS[familyName] || 'A powerful hero.'}`}
      style={{
      display: 'inline-flex', alignItems: 'center', gap: '3px',
      background: `${color}22`, border: `1px solid ${color}66`,
      color: color, borderRadius: 3,
      padding: '1px 6px', fontSize: '0.7em',
      fontFamily: 'Cinzel, serif', letterSpacing: '0.05em',
      marginTop: '0.3em',
      cursor: 'help',
    }}>
      {icon} {heroClass}
    </span>
  )
}

export function LevelBadge({ level, ascensionStar, large = false }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      background: 'rgba(201,168,76,0.1)', border: '1px solid rgba(201,168,76,0.3)',
      color: 'var(--gold)', borderRadius: 3,
      padding: large ? '2px 9px' : '1px 6px', fontSize: large ? '1.15em' : '0.7em',
      fontFamily: 'Cinzel, serif', marginLeft: '0.3em',
    }}>
      Lv.{level}
    </span>
  )
}

// Mirrors the real combat formula in calc_damage() (combat_service.py):
// below 40 morale, a hero's own damage output is multiplied by
// 0.5 + morale/80 — a sliding penalty, not a stepped one. At 40+ morale
// there is currently no penalty at all (the "shaken" tier is cosmetic only).
function moraleEffectDesc(morale) {
  if (morale >= 40) return 'No combat penalty at this morale.'
  const factor = 0.5 + morale / 80
  const pct = Math.round((1 - factor) * 100)
  return `Damage output reduced by ${pct}% while attacking, until morale recovers to 40+.`
}

export function MoraleBar({ morale, state }) {
  return (
    <div className="morale-bar-wrap" title={moraleEffectDesc(morale)} style={{ cursor: 'help' }}>
      <div className="morale-label">
        <span>Morale</span>
        <span className={`text-${state === 'steady' ? 'green' : state === 'broken' ? 'red' : 'gold'}`}>
          {MORALE_STATE_LABEL[state] || state} ({morale})
        </span>
      </div>
      <div className="morale-bar-bg">
        <div className={`morale-bar-fill ${state}`} style={{ width: `${morale}%` }} />
      </div>
    </div>
  )
}

export function HpBar({ health, maxHp }) {
  const pct = Math.max(0, Math.min(100, (health / maxHp) * 100))
  return (
    <div className="health-bar-wrap">
      <div className="morale-label">
        <span>Health</span>
        <span>{health} / {maxHp}</span>
      </div>
      <div className="health-bar-bg">
        <div className="health-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function AscensionStars({ count }) {
  if (!count || count <= 0) return null
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '2px',
      marginTop: '0.3em',
    }}>
      <span className="text-dim" style={{ fontSize: '0.65em', marginRight: '0.3em' }}>Ascension</span>
      {Array.from({ length: 7 }).map((_, i) => (
        <span key={i} style={{
          fontSize: '0.7em',
          color: i < count ? 'var(--gold)' : 'var(--border)',
          textShadow: i < count ? '0 0 4px rgba(201,168,76,0.5)' : 'none',
        }}>◆</span>
      ))}
    </div>
  )
}

function AptitudeDisplay({ hero }) {
  const level = hero.level || 1
  const reveals = Math.min(5, Math.floor(level / 5))
  const aptitudes = hero.aptitudes || {}

  return (
    <div style={{ marginTop: '0.5em' }}>
      <div className="text-dim" style={{ fontSize: '0.7em', marginBottom: '0.3em', fontFamily: 'Cinzel, serif' }}>
        Aptitudes
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2em' }}>
        {APTITUDE_ORDER.map((apt, index) => {
          const isRevealed = index < reveals
          const value = aptitudes[apt.toLowerCase()] ?? aptitudes[apt]
          return (
            <div key={apt} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              fontSize: '0.72em',
              padding: '0.15rem 0.4em',
              background: isRevealed ? 'rgba(255,255,255,0.03)' : 'transparent',
              borderRadius: 2,
            }}>
              <span className="text-dim">{apt}</span>
              {isRevealed && value != null ? (
                <span style={{
                  color: getAptitudeColor(value),
                  fontFamily: 'Cinzel, serif',
                  fontWeight: value >= 75 ? 'bold' : 'normal',
                }}>
                  {value}
                </span>
              ) : (
                <span style={{ color: 'var(--border)', fontStyle: 'italic', fontSize: '0.68em' }}>???</span>
              )}
            </div>
          )
        })}
      </div>
      {reveals < 5 && (
        <div className="text-dim" style={{ fontSize: '0.6em', marginTop: '0.2em', fontStyle: 'italic' }}>
          Next reveal at Lv.{(reveals + 1) * 5}
        </div>
      )}
    </div>
  )
}

export default function HeroCard({ hero, onAssign, onManageEquipment, selected, onClick, onToggleSelect, showFull = false, onRegenerateProfile, actions }) {
  if (!hero) return null
  const dead = !hero.is_alive
  const [refreshing, setRefreshing] = useState(false)
  const [cardImgError, setCardImgError] = useState(false)
  const [imgError, setImgError] = useState(false)
  const [retryKey, setRetryKey] = useState(0)
  const retryCountRef = React.useRef(0)
  const [showSynergyTip, setShowSynergyTip] = useState(false)

  const handleRegenerateProfile = async (e) => {
    e.stopPropagation()
    setRefreshing(true)
    try {
      await regenerateProfile(hero.id)
      if (onRegenerateProfile) onRegenerateProfile()
    } catch (err) {
      console.error(err)
    } finally {
      setRefreshing(false)
    }
  }

  // Backstory unlocking based on star rank
  const activeStar = hero.current_star || hero.birth_star
  // If 5+ star, show full story. If 1-4 star, show proportional percentage.
  const unlockPct = Math.min(1.0, activeStar / 5)
  const totalChars = hero.backstory ? hero.backstory.length : 0
  const visibleChars = Math.floor(totalChars * unlockPct)
  const unlockedStory = hero.backstory ? hero.backstory.substring(0, visibleChars) : ''
  const lockedStory = hero.backstory ? hero.backstory.substring(visibleChars).replace(/[a-zA-Z0-9]/g, '█') : ''

  return (
    <div
      className={`hero-card ${selected ? 'selected' : ''} ${dead ? 'dead' : ''} ${showFull ? 'full' : ''}`} style={{ fontSize: showFull ? "1.6em" : "1em" }}
      onClick={!dead && onClick ? onClick : undefined}
    >
      {onToggleSelect && (
        <div 
          onClick={(e) => { e.stopPropagation(); onToggleSelect(); }}
          style={{
            position: 'absolute', top: 5, left: 5, zIndex: 10,
            width: 20, height: 20, borderRadius: '50%',
            border: '2px solid var(--border-light)',
            background: selected ? 'var(--gold)' : 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer',
            color: '#000', fontSize: '0.8em', fontWeight: 'bold'
          }}
        >
          {selected && '✓'}
        </div>
      )}
      <CardFrame birthStar={hero.birth_star} style={{ position: 'relative', flexShrink: 0 }}>
        {hero.is_on_team > 0 && !showFull && (
          <div style={{
            position: 'absolute', top: 5, right: 5, zIndex: 10,
            background: 'rgba(64, 96, 200, 0.9)', color: '#fff', fontSize: '0.65em',
            padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold',
            border: '1px solid rgba(255,255,255,0.3)'
          }}>
            T{hero.is_on_team}
          </div>
        )}
        {hero.portrait_path && !imgError && !hero.portrait_path.includes('default_') ? (
          <img
            key={retryKey}
            src={cardImgError
              ? `http://localhost:8000/${hero.portrait_path}?t=${new Date().getTime()}`
              : `http://localhost:8000/heroes/${hero.id}/card-image?t=${new Date().getTime()}`}
            alt={hero.name}
            className="hero-portrait"
            draggable={false}
            style={showFull ? { height: 'auto', maxHeight: '700px', objectFit: 'contain' } : {}}
            onError={() => {
              // A transient failure (composite still being prewarmed, brief
              // backend hiccup) shouldn't permanently stick on the
              // placeholder — retry the current URL a couple times before
              // falling through to the next fallback stage.
              if (retryCountRef.current < 2) {
                retryCountRef.current += 1
                setTimeout(() => setRetryKey(k => k + 1), 1500)
                return
              }
              retryCountRef.current = 0
              if (cardImgError) setImgError(true)
              else setCardImgError(true)
            }}
          />
        ) : (
          <div className="hero-portrait-placeholder" style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center',
            background: `radial-gradient(circle at top, ${CLASS_COLORS[hero.hero_class] || '#444'}, #1a1a24)`,
            ...(showFull ? { height: '400px' } : {}),
            width: '100%',
            position: 'relative',
            overflow: 'hidden'
          }}>
            <span style={{ fontSize: showFull ? '4em' : '2.5em', opacity: 0.5, marginBottom: '20px' }}>
              {CLASS_ICONS[hero.hero_class] || '⚔'}
            </span>
            <div style={{
              position: 'absolute', bottom: '15px', left: 0, right: 0,
              textAlign: 'center', background: 'rgba(200, 50, 50, 0.8)',
              color: 'white', fontSize: '0.65em', padding: '2px',
              fontWeight: 'bold', textTransform: 'uppercase'
            }}>
              Placeholder (Regenerate Profile)
            </div>
          </div>
        )}
        
        {showFull && !dead && (
          <button
            className="btn btn-gold"
            style={{ position: 'absolute', bottom: '5px', right: '5px', padding: '2px 6px', fontSize: '0.6em' }}
            onClick={handleRegenerateProfile}
            disabled={refreshing}
            title="Reroll this hero's portrait — keeps their name, lore, and stats."
          >
            {refreshing ? '...' : 'Regenerate Portrait'}
          </button>
        )}
      </CardFrame>

      <div className="hero-name">{hero.name}</div>
      <div className="hero-title">{hero.title}</div>
      {hero.synergy_group && (
        <div style={{ marginTop: '0.4em', marginBottom: '0.2em', position: 'relative', display: 'inline-block' }}>
          <span
            onMouseEnter={(e) => { e.stopPropagation(); setShowSynergyTip(true) }}
            onMouseLeave={() => setShowSynergyTip(false)}
            style={{
              fontSize: '0.65em',
              background: 'rgba(200, 160, 48, 0.2)',
              color: '#e8c050',
              padding: '0.2rem 0.5em',
              borderRadius: '4px',
              fontFamily: 'Cinzel, serif',
              fontWeight: 'bold',
              border: '1px solid rgba(200, 160, 48, 0.4)',
              cursor: 'help',
            }}
          >
            <span style={{ marginRight: '4px' }}>🛡️</span>
            {hero.synergy_group}
          </span>
          {showSynergyTip && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              marginBottom: '6px',
              width: '220px',
              background: '#1a1a1a',
              border: '1px solid rgba(200, 160, 48, 0.5)',
              borderRadius: '4px',
              padding: '0.6em 0.7em',
              fontSize: '0.7em',
              fontFamily: 'inherit',
              fontWeight: 'normal',
              color: '#ddd',
              lineHeight: 1.4,
              zIndex: 20,
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              pointerEvents: 'none',
            }}>
              <strong style={{ color: '#e8c050' }}>{hero.synergy_group} Synergy</strong><br/>
              Deploying multiple "{hero.synergy_group}" heroes on the same team grants +5% STR/INT/AGI/Health per group member in combat (stacks with team size).
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.3em', marginTop: '0.3em' }}>
        <Stars count={hero.birth_star} />
        <LevelBadge level={hero.level || 1} ascensionStar={hero.ascension_star || 0} large={showFull} />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.3em', marginTop: '0.3em' }}>
        <ClassBadge heroClass={hero.hero_class} />
        {hero.ego_type && hero.ego_type.toLowerCase() !== 'null' && (
          <span
            title={`Ego Preference: ${EGO_TOOLTIPS[hero.ego_type] || 'Unknown desires.'}\nPatience: ${hero.ego_patience ?? 100}/100\n\n${
              hero.is_ego_satisfied === undefined ? '"I await deployment."' :
              hero.is_ego_satisfied ? '"This formation is acceptable."' :
              (hero.ego_patience ?? 100) > 50 ? '"This team composition displeases me. Fix it."' :
              '"My patience wears thin... I will take matters into my own hands soon."'
            }`}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '4px',
              background: 'rgba(255,100,100,0.1)', border: '1px solid rgba(255,100,100,0.3)',
              color: '#ff8888', borderRadius: 3,
              padding: '1px 6px', fontSize: '0.7em',
              fontFamily: 'Cinzel, serif',
              marginTop: '0.3em',
              cursor: 'help'
            }}>
            ⚡ Ego: {hero.ego_type}
            <span style={{ display: 'inline-block', width: '28px', height: '4px', background: 'rgba(255,255,255,0.15)', borderRadius: 2, overflow: 'hidden' }}>
              <span style={{
                display: 'block', height: '100%',
                width: `${hero.ego_patience ?? 100}%`,
                background: (hero.ego_patience ?? 100) <= 30 ? '#ff4444' : (hero.ego_patience ?? 100) <= 60 ? '#ffaa44' : '#88ff88',
              }} />
            </span>
          </span>
        )}
        {hero.is_team_leader && (
          <span title="Team Leader — sets the squad's tactical doctrine in combat (if they have an Ego, their preferences also shape the recommended lineup)." style={{
            display: 'inline-flex', alignItems: 'center', gap: '3px',
            background: 'rgba(201,168,76,0.15)', border: '1px solid rgba(201,168,76,0.4)',
            color: 'var(--gold)', borderRadius: 3,
            padding: '1px 6px', fontSize: '0.7em',
            fontFamily: 'Cinzel, serif', marginTop: '0.3em', cursor: 'help'
          }}>
            👑 Leader
          </span>
        )}
        {hero.battle_tendency && (
          <span title={BATTLE_TENDENCY_TOOLTIPS[hero.battle_tendency] || 'Their instinct in a fight.'} style={{
            display: 'inline-flex', alignItems: 'center', gap: '3px',
            background: 'rgba(140,140,160,0.12)', border: '1px solid rgba(140,140,160,0.35)',
            color: '#b0b0c8', borderRadius: 3,
            padding: '1px 6px', fontSize: '0.7em',
            fontFamily: 'Cinzel, serif', marginTop: '0.3em', cursor: 'help'
          }}>
            {hero.battle_tendency}
          </span>
        )}
        {hero.bonds && hero.bonds.length > 0 && (() => {
          // 1% stat boost per total bond level shared with current teammates
          // in combat (see bonds_service.get_team_bonds_multiplier) — only
          // actually applies when teammates with these bonds are deployed
          // together, but the total here is the cap that boost can reach.
          const totalBondLevel = hero.bonds.reduce((sum, b) => sum + b.bond_level, 0)
          const tooltip = [
            ...hero.bonds.map(b => `${b.hero_a_name} & ${b.hero_b_name} (Lv ${b.bond_level})`),
            `Up to +${totalBondLevel}% stats when bonded teammates fight together`,
          ].join('\n')
          return (
            <span
              title={tooltip}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '3px',
                background: 'rgba(255,105,180,0.15)', border: '1px solid rgba(255,105,180,0.4)',
                color: '#ff69b4', borderRadius: 3,
                padding: '1px 6px', fontSize: '0.7em',
                fontFamily: 'Cinzel, serif', marginTop: '0.3em', cursor: 'help'
              }}>
              ❤️ {hero.bonds.length} (+{totalBondLevel}%)
            </span>
          )
        })()}
        {hero.legacies && hero.legacies.length > 0 && (
          <span 
            title={hero.legacies.join('\n')}
            style={{
            display: 'inline-flex', alignItems: 'center', gap: '3px',
            background: 'rgba(180,180,255,0.15)', border: '1px solid rgba(180,180,255,0.4)',
            color: '#a0a0ff', borderRadius: 3,
            padding: '1px 6px', fontSize: '0.7em',
            fontFamily: 'Cinzel, serif', marginTop: '0.3em', cursor: 'help'
          }}>
            🕯️ {hero.legacies.length}
          </span>
        )}
        {hero.condition && hero.condition !== 'Normal' && (
          <span 
            title={hero.condition === 'Depressed' ? `Depressed (-75% Stats) until ${new Date(hero.condition_until).toLocaleString()}` : "Mind broken from Survivor's Guilt. Permanently retired from combat."}
            style={{
            display: 'inline-flex', alignItems: 'center', gap: '3px',
            background: hero.condition === 'Depressed' ? 'rgba(100,150,255,0.15)' : 'rgba(100,100,100,0.15)', border: `1px solid ${hero.condition === 'Depressed' ? 'rgba(100,150,255,0.4)' : 'rgba(100,100,100,0.4)'}`,
            color: hero.condition === 'Depressed' ? '#88bbff' : '#888', borderRadius: 3,
            padding: '1px 6px', fontSize: '0.7em',
            fontFamily: 'Cinzel, serif', marginTop: '0.3em', cursor: 'help'
          }}>
            {hero.condition === 'Depressed' ? '🌧️ Depressed' : '👴 Retired'}
          </span>
        )}
      </div>

      <div style={{ flex: 1 }} />

      {/* Ascension stars */}
      <AscensionStars count={hero.ascension_star || 0} />

      {dead && <div className="text-red text-sm" style={{ marginTop: '0.3em' }}>✦ Fallen</div>}

      {!dead && (
        <>
          <HpBar health={hero.health} maxHp={hero.max_health} />
          <MoraleBar morale={hero.morale} state={hero.morale_state || 'steady'} />

          <div className="stats-row">
            <div className="stat" title={`Base: ${hero.base_strength ?? hero.strength}`}>STR <span>{hero.strength}</span></div>
            <div className="stat" title={`Base: ${hero.base_intelligence ?? hero.intelligence}`}>INT <span>{hero.intelligence}</span></div>
            <div className="stat" title={`Base: ${hero.base_defense ?? hero.defense ?? 5}`}>DEF <span>{hero.defense ?? 5}</span></div>
            <div className="stat" title={`Base: ${hero.base_agility ?? hero.agility}`}>AGI <span>{hero.agility}</span></div>
          </div>

          {showFull && (
            <div style={{ marginTop: '0.75em', borderTop: '1px solid var(--border)', paddingTop: '0.75em' }}>
              <div className="stats-row" style={{ marginTop: '0.5em' }}>
                <div className="stat">Kills <span>{hero.kills}</span></div>
                <div className="stat">Floors <span>{hero.floors_survived}</span></div>
                <div className="stat">Stress <span>{hero.stress}</span></div>
                <div className="stat">Trauma <span>{hero.trauma}</span></div>
              </div>
              {hero.can_pilot === 1 && (
                <div style={{ marginTop: '0.4em', color: 'var(--blue)', fontSize: '0.75em' }}>
                  ⚙ Can pilot vessels
                </div>
              )}

              {/* Aptitude display */}
              <AptitudeDisplay hero={hero} />

              {/* Equipment Display */}
              <div style={{ marginTop: '0.75em' }}>
                <div className="text-dim" style={{ fontSize: '0.7em', marginBottom: '0.3em', fontFamily: 'Cinzel, serif' }}>
                  Equipment
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3em' }}>
                  {['weapon', 'armor', 'accessory'].map(slot => {
                    const eq = hero.equipment ? hero.equipment.find(e => e.type?.toLowerCase() === slot) : null;
                    return (
                      <div key={slot} style={{ 
                        padding: '0.3rem 0.5em', 
                        background: 'rgba(255,255,255,0.02)', 
                        borderLeft: `2px solid ${
                          !eq ? '#444' :
                          eq.rarity >= 5 ? '#c9a84c' : 
                          eq.rarity >= 4 ? '#8030c8' : 
                          eq.rarity >= 3 ? '#4a7aaa' : 
                          eq.rarity >= 2 ? '#4a9a6a' : '#888'
                        }`,
                        borderRadius: '0 3px 3px 0',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <div style={{ flex: 1, marginRight: '0.5em' }}>
                          <div style={{ fontSize: '0.65em', color: 'var(--text-dim)', textTransform: 'capitalize', marginBottom: '0.1em' }}>{slot}</div>
                          {eq ? (
                            <>
                              <div style={{ fontSize: '0.75em', color: 'var(--text-hi)' }}>{eq.name}</div>
                              {eq.stats_json && (
                                <div style={{ display: 'flex', gap: '0.4em', flexWrap: 'wrap', marginTop: '0.1em' }}>
                                  {Object.entries(JSON.parse(eq.stats_json)).map(([k, v]) => (
                                    <span key={k} className="text-green" style={{ fontSize: '0.6em' }}>
                                      +{v} {k.toUpperCase()}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </>
                          ) : (
                            <div style={{ fontSize: '0.75em', color: 'var(--text-dim)', fontStyle: 'italic' }}>Empty</div>
                          )}
                        </div>
                        {onManageEquipment && (
                          <button 
                            onClick={() => onManageEquipment(hero, slot, eq)}
                            style={{ 
                              background: eq ? 'transparent' : 'rgba(201,168,76,0.1)', 
                              border: eq ? '1px solid var(--border)' : '1px solid var(--gold)', 
                              color: eq ? 'var(--text-dim)' : 'var(--gold)', 
                              padding: '0.2rem 0.4em', 
                              borderRadius: '3px', 
                              cursor: 'pointer',
                              fontSize: '0.7em'
                            }}
                          >
                            {eq ? 'Unequip' : 'Equip'}
                          </button>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Traits Display */}
              {hero.traits && (
                <div style={{ marginTop: '0.75em' }}>
                  <div className="text-dim" style={{ fontSize: '0.7em', marginBottom: '0.3em', fontFamily: 'Cinzel, serif' }}>
                    Traits
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3em' }}>
                    {(() => {
                      try {
                        const traits = JSON.parse(hero.traits)
                        if (traits.length === 0) return <div className="text-dim text-sm" style={{ fontStyle: 'italic' }}>No unique traits.</div>
                        return traits.map((t, idx) => (
                          <div key={idx} style={{ 
                            padding: '0.3rem 0.5em', 
                            background: 'rgba(255,255,255,0.02)', 
                            borderLeft: `2px solid var(--gold)`,
                            borderRadius: '0 3px 3px 0'
                          }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.1em' }}>
                              <span style={{ fontSize: '0.75em', color: 'var(--text-hi)' }}>{t.name}</span>
                            </div>
                            <div className="text-dim" style={{ fontSize: '0.65em' }}>{t.desc}</div>
                          </div>
                        ))
                      } catch {
                        return <div className="text-dim text-sm" style={{ fontStyle: 'italic' }}>Trait data corrupted.</div>
                      }
                    })()}
                  </div>
                </div>
              )}

              {/* Skills Display */}
              {hero.skills && (
                <div style={{ marginTop: '0.75em' }}>
                  <div className="text-dim" style={{ fontSize: '0.7em', marginBottom: '0.3em', fontFamily: 'Cinzel, serif' }}>
                    Skills
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3em' }}>
                    {(() => {
                      try {
                        const skills = JSON.parse(hero.skills)
                        if (skills.length === 0) return <div className="text-dim text-sm" style={{ fontStyle: 'italic' }}>No skills learned.</div>
                        return skills.map((s, idx) => (
                          <div key={idx} style={{ 
                            padding: '0.3rem 0.5em', 
                            background: 'rgba(255,255,255,0.02)', 
                            borderLeft: `2px solid ${SKILL_RARITY_COLORS[s.rarity] || '#888'}`,
                            borderRadius: '0 3px 3px 0'
                          }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.1em' }}>
                              <span style={{ fontSize: '0.75em', color: SKILL_RARITY_COLORS[s.rarity] || 'var(--text-hi)' }}>{s.name}</span>
                              <span className="text-dim" style={{ fontSize: '0.65em', textTransform: 'uppercase' }}>{s.type} {s.cooldown ? `(${s.cooldown} CD)` : ''}</span>
                            </div>
                            {s.tier && (
                              <div style={{ fontSize: '0.65em', color: 'var(--gold)', marginBottom: '0.2em' }}>
                                {s.tier} Lv.{s.level} ({s.xp}/{s.max_xp} XP)
                              </div>
                            )}
                            <div className="text-dim" style={{ fontSize: '0.65em' }}>{s.desc}</div>
                          </div>
                        ))
                      } catch {
                        return <div className="text-dim text-sm" style={{ fontStyle: 'italic' }}>Skill data corrupted.</div>
                      }
                    })()}
                  </div>
                </div>
              )}
              
              <div className="story-block" style={{ marginTop: '1em', paddingTop: '0.75em', borderTop: '1px solid var(--border)' }}>
                <div className="text-dim" style={{ fontStyle: 'italic', lineHeight: 1.6 }}>
                  <span>{unlockedStory}</span>
                  {lockedStory && <span style={{ opacity: 0.3, letterSpacing: '2px' }}>{lockedStory}</span>}
                  {unlockPct < 1 && (
                    <div style={{ fontSize: '0.85em', color: 'var(--gold)', marginTop: '0.3em', opacity: 0.8 }}>
                      [Story locked. Promote hero to reveal more.]
                    </div>
                  )}
                </div>
                <div className="text-dim" style={{ marginTop: '0.4em', lineHeight: 1.5 }}>
                  {hero.personality}
                </div>
              </div>

              {actions && (
                <div style={{ marginTop: '1.2em', paddingTop: '0.8em', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                  {actions}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {selected && (
        <div style={{
          position: 'absolute', top: -6, right: -6,
          color: '#111', fontSize: '0.85em', background: 'var(--gold)',
          borderRadius: '50%', width: 22, height: 22,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 5px rgba(0,0,0,0.8)', zIndex: 20
        }}>✓</div>
      )}
    </div>
  )
}