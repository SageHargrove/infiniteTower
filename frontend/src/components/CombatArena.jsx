import React, { useState, useEffect, useRef } from 'react'
import { playHitSound } from '../audio'

const TEAM_POSITIONS = {
  hero: [
    { x: '34%', y: '30%' }, // Front Top
    { x: '34%', y: '70%' }, // Front Bottom
    { x: '14%', y: '15%' }, // Back Top
    { x: '14%', y: '50%' }, // Back Mid
    { x: '14%', y: '85%' }, // Back Bottom
  ],
  enemy: [
    { x: '66%', y: '30%' }, // Front Top
    { x: '66%', y: '70%' }, // Front Bottom
    { x: '86%', y: '15%' }, // Back Top
    { x: '86%', y: '50%' }, // Back Mid
    { x: '86%', y: '85%' }, // Back Bottom
  ]
}

// Solo enemies (elite mobs, minibosses, bosses) read as more threatening when
// rendered bigger than a regular swarm/pack unit — scaled by tier, not just
// "is there one enemy on screen" so a true boss still reads as the biggest
// thing in the room.
const ENEMY_SIZE_TIERS = {
  normal:   { circle: 150, container: 170, icon: '2.8rem', name: '1rem',   pos: null },
  elite:    { circle: 220, container: 240, icon: '3.6rem', name: '1.15rem', pos: { x: '70%', y: '50%' } },
  miniboss: { circle: 320, container: 340, icon: '4.4rem', name: '1.3rem', pos: { x: '73%', y: '50%' } },
  boss:     { circle: 460, container: 480, icon: '5.5rem', name: '1.5rem', pos: { x: '77%', y: '50%' } },
  // Swarms (6+ units on one side) no longer fit the fixed 5-slot formation —
  // they're laid out on a grid (see getGridPosition) and sized down further
  // still as the count climbs, so a 20-rat horde doesn't overlap itself.
  swarm:    { circle: 80,  container: 90,  icon: '1.6rem', name: '0.68rem', pos: null },
  swarmTiny:{ circle: 56,  container: 64,  icon: '1.2rem', name: '0.6rem',  pos: null },
}

// TEAM_POSITIONS only has 5 hand-placed slots per side, matching the 5-hero
// team cap — fine for normal encounters, but a swarm (or a hero side padded
// out by a summoned Construct past 5 units) needs a layout that scales with
// however many units actually showed up. Lays units out in an evenly-spaced
// grid within that side's half of the arena instead of hand-placed slots.
function getGridPosition(idx, count, team) {
  const cols = Math.ceil(Math.sqrt(count * 1.4))
  const rows = Math.ceil(count / cols)
  const col = idx % cols
  const row = Math.floor(idx / cols)
  const [xMin, xMax] = team === 'hero' ? [6, 44] : [56, 94]
  const [yMin, yMax] = [8, 92]
  const x = xMin + ((col + 0.5) / cols) * (xMax - xMin)
  const y = rows > 1 ? yMin + ((row + 0.5) / rows) * (yMax - yMin) : 50
  return { x: `${x}%`, y: `${y}%` }
}

function FloatingDamage({ number, isCrit, onComplete }) {
  const [active, setActive] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => {
      setActive(false)
      if (onComplete) onComplete()
    }, 800)
    return () => clearTimeout(timer)
  }, [onComplete])

  if (!active) return null

  return (
    <div style={{
      position: 'absolute',
      top: '-20px',
      left: '50%',
      transform: 'translate(-50%, -100%)',
      color: isCrit ? '#ff4444' : '#fff',
      fontWeight: 'bold',
      fontSize: isCrit ? '1.8rem' : '1.2rem',
      textShadow: '0 2px 4px rgba(0,0,0,0.8)',
      animation: 'floatUpAndFade 0.8s ease-out forwards',
      zIndex: 100,
      pointerEvents: 'none'
    }}>
      -{number}
      {isCrit && <span style={{ fontSize: '0.8rem', display: 'block' }}>CRIT!</span>}
    </div>
  )
}

function CombatUnitSprite({ unit, team, position, teamCount = 1, pos: posOverride, isActive, isHit, health, maxHp, mana, maxMana, damageInfo, tier = 'normal' }) {
  const [imgError, setImgError] = useState(false)
  if (!unit) return null

  const isDead = health <= 0
  const hpPercent = Math.max(0, (health / maxHp) * 100)
  const manaPercent = maxMana > 0 ? Math.max(0, (mana / maxMana) * 100) : 0

  const pos = posOverride || (teamCount > 5 ? getGridPosition(position, teamCount, team) : TEAM_POSITIONS[team][position]) || TEAM_POSITIONS[team][0]
  // Heroes render ~30% larger than the shared enemy-tier sizing so faces
  // and HP/mana bars stay legible — was previously sharing ENEMY_SIZE_TIERS
  // 1:1 with enemies, which is tuned for "boss should look huge," not for
  // a hero player actually needs to read at a glance.
  const baseSize = ENEMY_SIZE_TIERS[tier] || ENEMY_SIZE_TIERS.normal
  const size = team === 'hero'
    ? { ...baseSize, circle: Math.round(baseSize.circle * 1.3), container: Math.round(baseSize.container * 1.3) }
    : baseSize

  return (
    <div style={{
      position: 'absolute',
      left: pos.x,
      top: pos.y,
      transform: `translate(-50%, -50%) ${isActive ? (team === 'hero' ? 'translateX(15px)' : 'translateX(-15px)') : ''}`,
      transition: 'transform 0.2s ease-out',
      opacity: isDead ? 0.3 : 1,
      filter: isDead ? 'grayscale(100%)' : isHit ? 'brightness(200%)' : 'none',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: '0.7rem',
      width: `${size.container}px`,
      zIndex: tier === 'boss' ? 5 : tier === 'miniboss' ? 4 : tier === 'elite' ? 3 : 1
    }}>
      <div style={{
        width: `${size.circle}px`,
        height: `${size.circle}px`,
        borderRadius: '50%',
        border: `${tier === 'normal' ? 4 : 5}px solid ${team === 'hero' ? 'var(--gold)' : '#a44'}`,
        overflow: 'hidden',
        position: 'relative',
        background: '#1a1a24',
        boxShadow: isActive
          ? `0 0 20px ${team === 'hero' ? 'var(--gold)' : '#a44'}`
          : tier !== 'normal' ? `0 0 14px ${team === 'hero' ? 'rgba(201,168,76,0.4)' : 'rgba(170,68,68,0.5)'}, 0 4px 10px rgba(0,0,0,0.5)`
          : '0 4px 10px rgba(0,0,0,0.5)'
      }}>
        {unit.portrait_path && !imgError ? (
          <img src={`http://localhost:8000/${unit.portrait_path}`} style={{ width: '100%', height: '100%', objectFit: 'contain', objectPosition: 'center top' }} alt={unit.name} onError={() => setImgError(true)} />
        ) : (
          <div style={{ width: '100%', height: '100%', background: '#333', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: size.icon }}>
            {team === 'hero' ? '⚔' : '💀'}
          </div>
        )}
      </div>

      <div style={{
        width: '100%',
        background: '#111',
        height: '10px',
        borderRadius: '5px',
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${hpPercent}%`,
          height: '100%',
          background: team === 'hero' ? '#4a4' : '#e44',
          transition: 'width 0.3s ease-out'
        }} />
      </div>

      {team === 'hero' && maxMana > 0 && (
        <div title={`MP: ${mana} / ${maxMana}`} style={{
          width: '100%',
          background: '#111',
          height: '7px',
          borderRadius: '4px',
          overflow: 'hidden',
          marginTop: '-0.35rem',
        }}>
          <div style={{
            width: `${manaPercent}%`,
            height: '100%',
            background: '#3a7bd5',
            transition: 'width 0.3s ease-out',
          }} />
        </div>
      )}

      <div style={{
        fontSize: size.name,
        background: 'rgba(0,0,0,0.6)',
        padding: '0.15rem 0.6rem',
        borderRadius: '4px',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        maxWidth: '100%'
      }}>
        {unit.name}{unit.level ? ` [Lv ${unit.level}]` : ''}
      </div>

      {damageInfo && (
        <FloatingDamage number={damageInfo.amount} isCrit={damageInfo.crit} />
      )}
    </div>
  )
}

export default function CombatArena({ combatData, onComplete, turnNarrations }) {
  const [currentTurnIndex, setCurrentTurnIndex] = useState(-1)
  const [playing, setPlaying] = useState(false)
  
  // Local state for Health/Mana tracking
  const [unitHPs, setUnitHPs] = useState({})
  const [unitManas, setUnitManas] = useState({})
  
  const heroes = combatData?.initial_state?.heroes || []
  const enemies = combatData?.initial_state?.enemies || []
  const turns = combatData?.turns || []
  const isBoss = combatData?.initial_state?.is_boss || false
  const isMiniboss = combatData?.initial_state?.is_miniboss || false
  const isSurvivalSwarm = combatData?.initial_state?.is_survival_swarm || false
  const turnLimit = combatData?.initial_state?.turn_limit || null

  // Solo enemies (elite mobs, minibosses, bosses) read as more threatening
  // rendered bigger than a regular swarm/pack unit. A true boss is sized to
  // dominate its entire side of the field. Swarms (6+) drop to a smaller,
  // grid-laid-out size instead — see getGridPosition/ENEMY_SIZE_TIERS.swarm*.
  const enemyTier = isBoss ? 'boss' : isMiniboss ? 'miniboss'
    : enemies.length === 1 ? 'elite'
    : enemies.length > 12 ? 'swarmTiny'
    : enemies.length > 5 ? 'swarm'
    : 'normal'
  const heroTier = heroes.length > 5 ? 'swarm' : 'normal'
  const soloEnemyPos = enemies.length === 1 ? ENEMY_SIZE_TIERS[enemyTier].pos : null

  // Hit-sound archetype, reusing the same power_stat/is_ranged fields combat
  // already tracks per-unit instead of a separate per-class sound table —
  // a caster's hits chime, a ranged attacker thwips, melee clangs, enemies
  // get one shared growl.
  function classifyAttacker(unitId) {
    const hero = heroes.find(h => h.id === unitId)
    if (!hero) return 'enemy'
    if (hero.power_stat === 'intelligence') return 'caster'
    if (hero.is_ranged) return 'ranged'
    return 'melee'
  }

  useEffect(() => {
    if (combatData) {
      // Initialize HPs/Manas
      const initialHps = {}
      const initialManas = {}
      heroes.forEach(h => { initialHps[h.id] = h.health; initialManas[h.id] = h.mana })
      enemies.forEach(e => initialHps[e.id] = e.health)
      setUnitHPs(initialHps)
      setUnitManas(initialManas)
      setCurrentTurnIndex(-1)
      setPlaying(true)
    }
  }, [combatData])

  useEffect(() => {
    if (!playing) return

    if (currentTurnIndex >= turns.length) {
      setPlaying(false)
      setTimeout(() => {
        if (onComplete) onComplete()
      }, 1500)
      return
    }

    if (currentTurnIndex >= 0) {
      const turn = turns[currentTurnIndex]
      if (turn && turn.target_id) {
        setUnitHPs(prev => ({
          ...prev,
          [turn.target_id]: turn.target_hp
        }))
        if (turn.attacker_mana != null || turn.target_mana != null) {
          setUnitManas(prev => ({
            ...prev,
            ...(turn.attacker_mana != null ? { [turn.attacker_id]: turn.attacker_mana } : {}),
            ...(turn.target_mana != null ? { [turn.target_id]: turn.target_mana } : {}),
          }))
        }
        playHitSound(classifyAttacker(turn.attacker_id), turn.is_crit)
      }
    }

    const timer = setTimeout(() => {
      setCurrentTurnIndex(c => c + 1)
    }, 800) // Delay between turns

    return () => clearTimeout(timer)
  }, [currentTurnIndex, playing, turns, onComplete])

  const logEndRef = useRef(null)

  // Damage numbers stay on the sprites in the arena itself — this is a
  // separate running feed of the flavor text, building up turn by turn so
  // players can scroll back through what's happened instead of only ever
  // seeing the current turn's line before it's replaced by the next one.
  const revealedLines = []
  for (let i = 0; i <= currentTurnIndex && i < turns.length; i++) {
    revealedLines.push({ key: i, text: turnNarrations?.[i] || turns[i].log })
  }

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ block: 'end' })
  }, [revealedLines.length])

  if (!combatData || combatData.awaiting_choice) return null

  const currentTurn = currentTurnIndex >= 0 && currentTurnIndex < turns.length ? turns[currentTurnIndex] : null

  return (
    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'stretch' }}>
    <div style={{
      position: 'relative',
      flex: '1 1 auto',
      minWidth: 0,
      height: '880px',
      background: 'linear-gradient(to bottom, #1a1a24, #0a0a10)',
      border: '1px solid #333',
      borderRadius: '8px',
      overflow: 'hidden',
      marginBottom: '1rem',
      boxShadow: 'inset 0 0 50px rgba(0,0,0,0.8)'
    }}>
      {/* Background elements */}
      <div style={{ position: 'absolute', inset: 0, opacity: 0.1, backgroundImage: 'url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAABZJREFUeNpi2r9//38bIxsDB1AMBgwAE2gDG9mC9U8AAAAASUVORK5CYII=)', backgroundSize: '10px' }} />
      
      {/* Divider */}
      <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '2px', background: 'rgba(255,255,255,0.05)' }} />

      {/* Survival Floor round counter — frames the fight as "outlast the
          clock," not "kill count," since the normal enemies-remaining
          framing would be misleading here (the swarm isn't meant to hit 0). */}
      {isSurvivalSwarm && turnLimit && (
        <div style={{
          position: 'absolute', top: '10px', left: '50%', transform: 'translateX(-50%)',
          zIndex: 50, background: 'rgba(10,10,14,0.85)', border: '1px solid rgba(201,168,76,0.4)',
          borderRadius: '6px', padding: '0.4rem 1rem', fontFamily: 'Cinzel, serif',
          color: 'var(--gold)', fontSize: '0.95rem', letterSpacing: 1, textTransform: 'uppercase',
          boxShadow: '0 2px 10px rgba(0,0,0,0.5)',
        }}>
          Survive! Round {Math.min(currentTurn?.round || 1, turnLimit)} / {turnLimit}
        </div>
      )}

      {/* Render Heroes */}
      {heroes.map((hero, idx) => {
        const isAttacker = currentTurn?.attacker_id === hero.id
        const isTarget = currentTurn?.target_id === hero.id
        const dmgInfo = isTarget ? { amount: currentTurn.damage, crit: currentTurn.is_crit } : null
        return (
          <CombatUnitSprite
            key={hero.id}
            unit={hero}
            team="hero"
            position={idx}
            teamCount={heroes.length}
            tier={heroTier}
            isActive={isAttacker}
            isHit={isTarget}
            health={unitHPs[hero.id] ?? hero.health}
            maxHp={hero.max_health}
            mana={unitManas[hero.id] ?? hero.mana}
            maxMana={hero.max_mana}
            damageInfo={dmgInfo}
          />
        )
      })}

      {/* Render Enemies */}
      {enemies.map((enemy, idx) => {
        const isAttacker = currentTurn?.attacker_id === enemy.id
        const isTarget = currentTurn?.target_id === enemy.id
        const dmgInfo = isTarget ? { amount: currentTurn.damage, crit: currentTurn.is_crit } : null
        return (
          <CombatUnitSprite
            key={enemy.id}
            unit={enemy}
            team="enemy"
            position={idx}
            teamCount={enemies.length}
            pos={soloEnemyPos}
            tier={enemyTier}
            isActive={isAttacker}
            isHit={isTarget}
            health={unitHPs[enemy.id] ?? enemy.health}
            maxHp={enemy.max_health}
            damageInfo={dmgInfo}
          />
        )
      })}

      <style>{`
        @keyframes floatUpAndFade {
          0% { transform: translate(-50%, 0) scale(0.5); opacity: 0; }
          20% { transform: translate(-50%, -20px) scale(1.2); opacity: 1; }
          100% { transform: translate(-50%, -40px) scale(1); opacity: 0; }
        }
        @keyframes logLineIn {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>

    {/* Battle Log — damage numbers stay on the sprites above; this is just
        the flavor text, building up as a scrollable history. */}
    <div style={{
      flex: '0 0 220px',
      height: '880px',
      background: 'rgba(10,10,14,0.9)',
      border: '1px solid #333',
      borderRadius: '8px',
      marginBottom: '1rem',
      padding: '0.75rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.5rem',
      overflowY: 'auto',
    }}>
      <div style={{ fontFamily: 'Cinzel, serif', color: 'var(--gold)', fontSize: '0.8rem', letterSpacing: 1, textTransform: 'uppercase', marginBottom: '0.25rem', flexShrink: 0 }}>
        Battle Log
      </div>
      {revealedLines.map(line => (
        <div key={line.key} style={{
          fontSize: '0.8rem',
          lineHeight: 1.4,
          color: '#ddd',
          borderLeft: '2px solid rgba(201,168,76,0.4)',
          paddingLeft: '0.5rem',
          animation: 'logLineIn 0.2s ease-out',
        }}>
          {line.text}
        </div>
      ))}
      <div ref={logEndRef} />
    </div>
    </div>
  )
}
