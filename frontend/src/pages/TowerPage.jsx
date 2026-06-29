import React, { useState, useEffect } from 'react'
import { getAllTeams, getBase, enterFloor, resolveEvent, resolveExplore, previewFloor, getNarrative } from '../api/client'
import { arenaUpdateFloor, getArenaToken } from '../api/arenaServerClient'
import { emitToast } from '../toastBus'
import CombatArena from '../components/CombatArena'
import FairyGuide from '../components/FairyGuide'
import { CardFrame } from '../components/HeroCard'

const FLOOR_ICONS = {
  combat: '⚔️',
  miniboss: '💀',
  boss: '👿',
  resource: '💎',
  event: '❓',
  survival: '🛡️',
  defend: '🏰',
  explore: '🗺️',
  escort: '🤝',
  rest: '🏕️',
}

const FLOOR_TYPE_INFO = {
  combat: { color: '#a44', label: 'Combat', blurb: 'A standard fight.' },
  miniboss: { color: '#c63', label: 'Miniboss', blurb: 'A tougher single enemy.' },
  boss: { color: '#e33', label: 'Boss', blurb: 'The floor\'s guardian.' },
  event: { color: '#86c', label: 'Event', blurb: 'A choice encounter.' },
  survival: { color: '#c44', label: 'Survival', blurb: 'A fight against a larger enemy wave.' },
  defend: { color: '#64a', label: 'Defend', blurb: 'A fight to hold a chokepoint.' },
  explore: { color: '#4a6', label: 'Explore', blurb: 'A risk/reward discovery.' },
  escort: { color: '#c93', label: 'Escort', blurb: 'A fight to protect an NPC.' },
  rest: { color: '#3a5', label: 'Rest', blurb: 'Free healing, no combat.' },
}

function FloorBadge({ type }) {
  const info = FLOOR_TYPE_INFO[type]
  return (
    <span style={{
      background: info?.color || '#555',
      padding: '0.15rem 0.4rem',
      borderRadius: 4,
      fontSize: '0.7rem',
      textTransform: 'uppercase',
      letterSpacing: '0.5px'
    }}>
      {info?.label || type}
    </span>
  )
}

// Survival Swarm is a random 35%-chance ALTERNATIVE rolled inside a
// miniboss floor's combat resolution (services/combat_service.py's
// SWARM_SURVIVAL_CHANCE) — not its own floor type, so the static
// "Miniboss: A tougher single enemy" blurb was actively wrong (and
// confusing — see the 30-50 enemy swarm) whenever that roll landed.
const SURVIVAL_SWARM_INFO = { color: '#c44', label: 'Survival Swarm', blurb: 'An overwhelming horde — outlast the clock, don\'t try to clear it.' }

function FloorTypeCallout({ type, isSurvivalSwarm }) {
  const info = isSurvivalSwarm ? SURVIVAL_SWARM_INFO : FLOOR_TYPE_INFO[type]
  if (!info) return null
  return (
    <div style={{
      maxWidth: '600px',
      margin: '0 auto 1.5rem auto',
      textAlign: 'center',
      padding: '0.6rem 1rem',
      background: `${info.color}22`,
      border: `1px solid ${info.color}`,
      borderRadius: 6,
    }}>
      <span style={{ fontFamily: 'Cinzel, serif', textTransform: 'uppercase', letterSpacing: '1px', color: info.color }}>
        {info.label} Floor
      </span>
      <span className="text-dim" style={{ marginLeft: '0.6rem', fontSize: '0.85rem' }}>
        {info.blurb}
      </span>
    </div>
  )
}

// Multi-team floors run as N parallel arenas (see team_results), each with
// its own initial_state — the post-combat summary screen still wants one
// combined roster, so merge them here instead of duplicating this in both
// call sites.
function mergedCombatEntities(result) {
  const teamResults = (result?.combat?.team_results || result?.team_results || []).filter(Boolean)
  if (teamResults.length > 0) {
    const heroes = teamResults.flatMap(tr => tr.initial_state?.heroes || [])
    const enemies = teamResults.flatMap(tr => tr.initial_state?.enemies || [])
    return { heroes, enemies }
  }
  return result?.initial_state || result?.combat?.initial_state || null
}

function heroCombatStatus(heroId, lastResult, combatEntities) {
  if (lastResult.combat?.dead_heroes?.includes(heroId)) return 'kia'
  const surv = lastResult.combat?.surviving_heroes?.find(s => s.id === heroId)
  if (!surv) return 'unknown'
  const entity = combatEntities?.heroes?.find(h => h.id === heroId)
  if (entity && surv.health < entity.max_health) return 'injured'
  return 'alive'
}

function PostCombatScreen({ lastResult, combatEntities, onReturn, onRerun, busy }) {
  if (!lastResult) return null;

  const metrics = lastResult.combat?.combat_metrics || {};
  const maxDmg = Math.max(1, ...Object.values(metrics));
  const mvpId = Object.entries(metrics).sort((a, b) => b[1] - a[1])[0]?.[0]
  const wasVictory = !lastResult.run_over && lastResult.combat?.winner !== 'enemies';
  const continueLabel = wasVictory ? 'Continue' : 'Retreat'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', marginTop: '2rem' }}>

      {lastResult.narrative && (
        <div className="card" style={{ fontStyle: 'italic', color: 'var(--text-dim)', lineHeight: 1.6 }}>
          {lastResult.narrative}
        </div>
      )}

      {lastResult.chatter_line && (
        <div className="card" style={{ textAlign: 'center', borderColor: wasVictory ? 'var(--green)' : 'var(--red)' }}>
          <div style={{ fontStyle: 'italic', fontSize: '1.05rem' }}>"{lastResult.chatter_line.line}"</div>
          <div className="text-dim" style={{ fontSize: '0.8rem', marginTop: '0.3rem' }}>— {lastResult.chatter_line.name}</div>
        </div>
      )}

      {lastResult.level_up_chatter?.map((c, i) => (
        <div key={i} className="card" style={{ textAlign: 'center', borderColor: 'var(--gold)' }}>
          <div className="text-gold" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: 1, marginBottom: '0.3rem' }}>Level Up</div>
          <div style={{ fontStyle: 'italic', fontSize: '1.05rem' }}>"{c.line}"</div>
          <div className="text-dim" style={{ fontSize: '0.8rem', marginTop: '0.3rem' }}>— {c.name}</div>
        </div>
      ))}

      {/* Team Status */}
      <div className="card">
        <div className="section-header">Team Status</div>
        <div style={{ display: 'flex', gap: '1.2rem', flexWrap: 'wrap' }}>
          {combatEntities?.heroes?.map(h => {
            const status = heroCombatStatus(h.id, lastResult, combatEntities)
            const STATUS_LABEL = { injured: 'Injured', kia: 'Killed In Action' }
            const isMvp = (metrics[h.id] || 0) > 0 && String(h.id) === String(mvpId)
            return (
              <div key={h.id} style={{ width: 96, textAlign: 'center', position: 'relative' }}>
                {isMvp && (
                  <div title="MVP" style={{ position: 'absolute', top: -14, left: '50%', transform: 'translateX(-50%)', fontSize: '1.4rem', zIndex: 10, filter: 'drop-shadow(0 0 4px var(--star5))' }}>
                    👑
                  </div>
                )}
                <CardFrame birthStar={h.hero_star} status={status === 'alive' ? null : status} style={isMvp ? { boxShadow: '0 0 12px var(--star5)', border: '2px solid var(--star5)' } : undefined}>
                  {h.portrait_path ? (
                    <img
                      src={`http://localhost:8000/heroes/${h.id}/card-image?mini=true`}
                      draggable={false}
                      style={{ width: '100%', height: 96, objectFit: 'cover', objectPosition: 'center 15%', borderRadius: 4 }}
                      onError={(e) => { e.target.onerror = null; e.target.src = `http://localhost:8000/${h.portrait_path}` }}
                    />
                  ) : (
                    <div style={{ width: '100%', height: 96, borderRadius: 4, background: 'var(--bg-panel)' }} />
                  )}
                </CardFrame>
                <div style={{ fontSize: '0.72rem', marginTop: '0.3rem', color: isMvp ? 'var(--star5)' : undefined }}>{h.name}</div>
                {status !== 'alive' && status !== 'unknown' && (
                  <div className={status === 'injured' ? 'text-red' : 'text-dim'} style={{ fontSize: '0.62rem' }}>{STATUS_LABEL[status]}</div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>

        {/* Combat Metrics */}
        <div className="card">
          <div className="section-header">Combat Metrics</div>
          <div className="text-dim text-sm" style={{ marginBottom: '1rem' }}>Damage Dealt</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {combatEntities?.heroes?.map(h => {
              const dmg = metrics[h.id] || 0;
              const pct = (dmg / maxDmg) * 100;
              const isMvp = dmg > 0 && String(h.id) === String(mvpId)
              return (
                <div key={h.id}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.2rem' }}>
                    <span>{isMvp && '🏆 '}{h.name}{isMvp && <span className="text-gold" style={{ fontSize: '0.7rem', marginLeft: '0.4rem' }}>MVP</span>}</span>
                    <span className="text-gold">{dmg.toLocaleString()}</span>
                  </div>
                  <div style={{ height: '8px', background: '#222', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: isMvp ? 'var(--star5)' : 'var(--gold)', transition: 'width 1s ease-out', boxShadow: isMvp ? '0 0 8px var(--star5)' : 'none' }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Loot and Rewards */}
        <div className="card">
          <div className="section-header">Loot & Rewards</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

            {lastResult.gold_gained > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', borderRadius: 6 }}>
                <span>Gold Found</span>
                <span className="text-gold" style={{ fontFamily: 'Cinzel, serif' }}>+{lastResult.gold_gained.toLocaleString()}g</span>
              </div>
            )}

            {lastResult.gems_gained > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(0,255,255,0.08)', border: '1px solid rgba(0,255,255,0.3)', borderRadius: 6 }}>
                <span>New Floor Record!</span>
                <span style={{ color: '#00ffff', fontFamily: 'Cinzel, serif', textShadow: '0 0 5px rgba(0,255,255,0.5)' }}>+{lastResult.gems_gained.toLocaleString()} 💎</span>
              </div>
            )}

            {lastResult.supplies_gained > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', borderRadius: 6 }}>
                <span>Supplies Found</span>
                <span style={{ color: 'var(--text-hi)', fontFamily: 'Cinzel, serif' }}>+{lastResult.supplies_gained.toLocaleString()}</span>
              </div>
            )}
            
            {lastResult.materials_gained && Object.keys(lastResult.materials_gained).length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', borderRadius: 6 }}>
                <span>Materials Found</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  {Object.entries(lastResult.materials_gained).map(([mat, qty]) => (
                    <div key={mat} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                      <span className="text-dim">{mat}</span>
                      <span style={{ color: 'var(--text-hi)', fontFamily: 'Cinzel, serif' }}>+{qty}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {lastResult.equipment_drop && (
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(74,154,106,0.1)', border: '1px solid var(--green)', borderRadius: 6 }}>
                <span style={{ color: 'var(--green)' }}>Equipment Dropped</span>
                <span>{lastResult.equipment_drop.name} ({lastResult.equipment_drop.rarity})</span>
              </div>
            )}

            {lastResult.blueprint_found && (
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(201,168,76,0.1)', border: '1px solid var(--gold)', borderRadius: 6 }}>
                <span className="text-gold">📜 Blueprint Found</span>
                <span>{lastResult.blueprint_found}</span>
              </div>
            )}

            {lastResult.combat?.skill_upgrades && Object.entries(lastResult.combat.skill_upgrades).map(([hid, ups]) => (
              ups.map((u, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(157,78,221,0.1)', border: '1px solid #9d4edd', borderRadius: 6 }}>
                  <span style={{ color: '#e0aaff' }}>Skill Ascended</span>
                  <span>{u.skill_name} ➔ {u.new_tier}</span>
                </div>
              ))
            ))}

            {lastResult.level_ups && lastResult.level_ups.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', padding: '0.75rem', background: 'rgba(201,168,76,0.1)', border: '1px solid var(--gold)', borderRadius: 6 }}>
                <span className="text-gold" style={{ fontFamily: 'Cinzel, serif' }}>⬆ Level Up</span>
                {lastResult.level_ups.map((msg, i) => (
                  <div key={i} style={{ fontSize: '0.85rem', color: msg.startsWith('  ') ? 'var(--star5)' : 'var(--text-hi)' }}>{msg}</div>
                ))}
              </div>
            )}

            {(!lastResult.gold_gained && !lastResult.gems_gained && !lastResult.equipment_drop && !lastResult.blueprint_found && !lastResult.combat?.skill_upgrades && !lastResult.supplies_gained && !(lastResult.level_ups && lastResult.level_ups.length > 0) && !(lastResult.materials_gained && Object.keys(lastResult.materials_gained).length > 0)) && (
               <div className="text-dim text-center" style={{ padding: '2rem' }}>No loot found.</div>
            )}

          </div>
        </div>
      </div>
      
      {/* Victory / Defeat / Continue Block */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
         <div style={{
           padding: '1rem', width: '100%', borderRadius: 6,
           background: wasVictory ? 'rgba(201,168,76,0.1)' : 'rgba(192,64,64,0.1)',
           border: `1px solid ${wasVictory ? 'var(--gold)' : '#c44'}`
         }}>
           <div style={{
             fontSize: '1.5rem', fontFamily: 'Cinzel, serif', textAlign: 'center', letterSpacing: '2px',
             color: wasVictory ? 'var(--gold)' : '#e66'
           }}>
             {wasVictory ? 'Victory!' : 'Defeat...'}
           </div>
         </div>
         <div style={{ display: 'flex', gap: '1rem', width: '100%' }}>
           <button className="btn" onClick={onRerun} disabled={busy} style={{ flex: 1, padding: '1rem', fontSize: '1.1rem', letterSpacing: '1px' }}>
             Rerun Floor
           </button>
           <button className="btn btn-primary" onClick={onReturn} disabled={busy} style={{ flex: 1, padding: '1rem', fontSize: '1.1rem', letterSpacing: '1px' }}>
             {continueLabel}
           </button>
         </div>
      </div>

    </div>
  )
}

export default function TowerPage({ onGoldChange }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  const [team, setTeam] = useState({})
  const [base, setBase] = useState(null)
  const [highestFloor, setHighestFloor] = useState(0)

  // GUI State
  const [selectedZone, setSelectedZone] = useState(0)
  const [selectedFloor, setSelectedFloor] = useState(1)
  const [resolvedFloor, setResolvedFloor] = useState(null)
  const [deployTeamIds, setDeployTeamIds] = useState([1, 2, 3, 4, 5])

  // Combat/Event State
  const [advancing, setAdvancing] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [pendingEvent, setPendingEvent] = useState(null)
  const [resolving, setResolving] = useState(false)
  const [eventResolution, setEventResolution] = useState(null)
  const [pendingExplore, setPendingExplore] = useState(null)
  const [exploreResolution, setExploreResolution] = useState(null)
  
  const [combatEntities, setCombatEntities] = useState(null)
  const [postCombatPhase, setPostCombatPhase] = useState(false)
  const [arenasFinished, setArenasFinished] = useState(0)
  // Indexed by team/arena position — one AI-narrated line per turn, swapped
  // in for the raw damage-number log line once it arrives (see pollTurnNarrative).
  const [turnNarrations, setTurnNarrations] = useState({})
  const [floorPreview, setFloorPreview] = useState(null)

  useEffect(() => {
    refresh()
  }, [])

  useEffect(() => {
    if (lastResult) return
    if (selectedFloor <= highestFloor) {
      setFloorPreview(null)
      return
    }
    let cancelled = false
    previewFloor(selectedFloor).then(p => { if (!cancelled) setFloorPreview(p) }).catch(() => {})
    return () => { cancelled = true }
  }, [selectedFloor, highestFloor, lastResult])

  useEffect(() => {
    // Silently sync highest_floor to the Arena server if logged in
    if (highestFloor > 0 && getArenaToken()) {
      arenaUpdateFloor(highestFloor).catch(() => {})
    }
  }, [highestFloor])

  async function refresh() {
    setLoading(true)
    try {
      const [teamsData, baseData] = await Promise.all([getAllTeams(), getBase()]);
      setHighestFloor(baseData.highest_floor || 0);
      setTeam(teamsData)
      setBase(baseData)
      
      if (!lastResult && baseData.highest_floor > 0) {
        const nextFloor = baseData.highest_floor + 1
        setSelectedFloor(nextFloor)
        setSelectedZone(Math.floor((nextFloor - 1) / 10))
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  function pollNarrative(narrativeId, attemptsLeft = 4) {
    if (!narrativeId || attemptsLeft <= 0) return
    setTimeout(async () => {
      try {
        const res = await getNarrative(narrativeId)
        if (res.ready && res.narrative) {
          setLastResult(prev => prev ? { ...prev, narrative: res.narrative } : prev)
        } else {
          pollNarrative(narrativeId, attemptsLeft - 1)
        }
      } catch {
        // Flavor text only — silently give up on failure.
      }
    }, 2000)
  }

  // Polls more frequently/eagerly than pollNarrative — combat plays out at
  // 800ms/turn, so the per-turn narration array needs to land mid-fight to
  // be useful, not after the player's already watched the whole thing play
  // out with raw damage-number lines.
  function pollTurnNarrative(narrativeId, arenaIndex, attemptsLeft = 6) {
    if (narrativeId == null || attemptsLeft <= 0) return
    setTimeout(async () => {
      try {
        const res = await getNarrative(narrativeId)
        if (res.ready && Array.isArray(res.narrative)) {
          setTurnNarrations(prev => ({ ...prev, [arenaIndex]: res.narrative }))
        } else if (!res.ready) {
          pollTurnNarrative(narrativeId, arenaIndex, attemptsLeft - 1)
        }
      } catch {
        // Flavor text only — silently give up on failure.
      }
    }, 1000)
  }

  async function enterFloorFlow(floorNumber, { skipAnimation = false } = {}) {
    setAdvancing(true)
    setError(null)
    setEventResolution(null)
    setPendingEvent(null)
    setExploreResolution(null)
    setPendingExplore(null)
    setLastResult(null)
    setResolvedFloor(floorNumber)
    setCombatEntities(null)
    setPostCombatPhase(false)
    setArenasFinished(0)
    setTurnNarrations({})

    try {
      const requiredTeams = (floorNumber - 1) === 0 ? 1 : Math.floor((floorNumber - 1) / 20) + 1
      const result = await enterFloor(floorNumber, deployTeamIds.slice(0, requiredTeams))
      setLastResult(result)
      setCombatEntities(mergedCombatEntities(result))
      if (result.narrative_id) pollNarrative(result.narrative_id)
      const tnIds = result.turn_narrative_ids || (result.turn_narrative_id != null ? [result.turn_narrative_id] : [])
      tnIds.forEach((id, i) => pollTurnNarrative(id, i))

      if (result.awaiting_choice && result.event) {
        setPendingEvent(result)
      } else if (result.awaiting_choice && result.explore) {
        setPendingExplore(result)
      } else if (skipAnimation) {
        // Already seen this floor — jump straight to the resolution screen
        // instead of replaying the full combat animation.
        setPostCombatPhase(true)
      }

      await refresh()
      if (onGoldChange) onGoldChange()
    } catch (e) {
      setError(e.message)
    } finally {
      setAdvancing(false)
    }
  }

  function handleEnterFloor() {
    return enterFloorFlow(selectedFloor)
  }

  function handleSkipFloor() {
    return enterFloorFlow(selectedFloor, { skipAnimation: true })
  }

  function handleRerun() {
    return enterFloorFlow(resolvedFloor || selectedFloor, { skipAnimation: true })
  }

  function handleExit() {
    setLastResult(null)
    setEventResolution(null)
    setExploreResolution(null)
    setPendingEvent(null)
    setPendingExplore(null)
    setAllLogs([])
    setPostCombatPhase(false)
  }

  async function handleEventChoice(choiceId) {
    setResolving(true)
    setError(null)
    try {
      const requiredTeams = ((resolvedFloor || selectedFloor) - 1) === 0 ? 1 : Math.floor(((resolvedFloor || selectedFloor) - 1) / 20) + 1
      const result = await resolveEvent(resolvedFloor || selectedFloor, deployTeamIds.slice(0, requiredTeams), pendingEvent.event.id, choiceId, pendingEvent.theme)
      setEventResolution(result)
      setPendingEvent(null)

      setPostCombatPhase(true);

      await refresh()
      if (onGoldChange) onGoldChange()
    } catch (e) {
      setError(e.message)
    } finally {
      setResolving(false)
    }
  }

  async function handleExploreChoice(choiceId) {
    setResolving(true)
    setError(null)
    try {
      const requiredTeams = ((resolvedFloor || selectedFloor) - 1) === 0 ? 1 : Math.floor(((resolvedFloor || selectedFloor) - 1) / 20) + 1
      const result = await resolveExplore(resolvedFloor || selectedFloor, deployTeamIds.slice(0, requiredTeams), choiceId)
      // Explore always ends in a real fight now — route through the same
      // combat animation as a normal floor, instead of jumping straight to
      // a static result box.
      setExploreResolution(result)
      setLastResult(result)
      setArenasFinished(0)
      setTurnNarrations({})
      setCombatEntities(mergedCombatEntities(result))
      setPendingExplore(null)
      const tnIds = result.turn_narrative_ids || (result.turn_narrative_id != null ? [result.turn_narrative_id] : [])
      tnIds.forEach((id, i) => pollTurnNarrative(id, i))

      await refresh()
      if (onGoldChange) onGoldChange()
    } catch (e) {
      setError(e.message)
    } finally {
      setResolving(false)
    }
  }

  if (loading) return <div className="page text-dim">Loading...</div>

  const maxZone = Math.floor(highestFloor / 10)
  const startFloorOfZone = selectedZone * 10 + 1

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div className="section-header" style={{ marginBottom: 0 }}>The Tower</div>
      </div>

      {lastResult ? (
        <div>
          {/* Centered Resolution Header */}
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <div className="text-dim text-sm" style={{ letterSpacing: 2, textTransform: 'uppercase' }}>Resolution</div>
            <div style={{ fontFamily: 'Cinzel, serif', fontSize: '3rem', color: 'var(--gold)', textShadow: '0 2px 10px rgba(201,168,76,0.3)' }}>
              Floor {resolvedFloor}
            </div>
          </div>

          {lastResult && <FloorTypeCallout type={lastResult.floor_type} isSurvivalSwarm={
            (lastResult.combat?.team_results || lastResult.team_results || []).some(tr => tr?.initial_state?.is_survival_swarm)
            || lastResult.combat?.initial_state?.is_survival_swarm
            || lastResult.initial_state?.is_survival_swarm
          } />}

          {postCombatPhase && lastResult.run_over && (
            <div className="text-red" style={{ maxWidth: '600px', margin: '0 auto 2rem auto', textAlign: 'center', padding: '1rem', background: 'rgba(192,64,64,0.1)', border: '1px solid #c44', borderRadius: 6 }}>
              ✦ The team was defeated and forced to retreat.
            </div>
          )}

          {error && <div className="text-red text-center" style={{ marginBottom: '1rem' }}>{error}</div>}

          {/* Event UI (Interrupts combat flow if awaiting choice) */}
          {pendingEvent && !postCombatPhase && (
            <div className="card" style={{ maxWidth: '600px', margin: '0 auto 2rem auto', border: '1px solid var(--gold)' }}>
              <div style={{ fontFamily: 'Cinzel, serif', color: 'var(--gold)', fontSize: '1.2rem', marginBottom: '1rem', textAlign: 'center' }}>
                Event: {pendingEvent.event.name}
              </div>
              <div style={{ marginBottom: '1.5rem', lineHeight: 1.6, color: 'var(--text-hi)', fontSize: '1.05rem', textAlign: 'center' }}>
                {pendingEvent.event.description}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {pendingEvent.event.choices.map(choice => (
                  <button 
                    key={choice.id}
                    className="btn"
                    onClick={() => handleEventChoice(choice.id)}
                    disabled={resolving}
                    style={{
                      textAlign: 'center',
                      padding: '1rem',
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      fontSize: '1rem',
                      userSelect: 'none',
                      WebkitUserSelect: 'none',
                    }}
                    onMouseOver={e => {
                      if (!resolving) e.target.style.background = 'rgba(255,255,255,0.1)'
                    }}
                    onMouseOut={e => {
                      if (!resolving) e.target.style.background = 'rgba(0,0,0,0.3)'
                    }}
                  >
                    <div style={{ color: 'var(--text-hi)' }}>
                      {choice.label || choice.text || `Choice ${choice.id}`}
                    </div>
                    {choice.hint && (
                      <div className="text-dim" style={{ fontSize: '0.8rem', marginTop: '0.3rem', fontStyle: 'italic' }}>
                        {choice.hint}
                      </div>
                    )}
                  </button>
                ))}
              </div>

              {resolving && (
                <div className="text-dim text-center" style={{ marginTop: '1rem' }}>
                  Resolving...
                </div>
              )}
              <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                <button className="btn" onClick={handleExit} disabled={resolving} style={{ padding: '0.5rem 1.5rem', fontSize: '0.9rem' }}>
                  Exit
                </button>
              </div>
            </div>
          )}

          {/* Explore UI (Interrupts combat flow if awaiting choice) */}
          {pendingExplore && !postCombatPhase && (
            <div className="card" style={{ maxWidth: '600px', margin: '0 auto 2rem auto', border: '1px solid var(--green)' }}>
              <div style={{ fontFamily: 'Cinzel, serif', color: 'var(--green)', fontSize: '1.2rem', marginBottom: '1rem', textAlign: 'center' }}>
                Explore
              </div>
              <div style={{ marginBottom: '1.5rem', lineHeight: 1.6, color: 'var(--text-hi)', fontSize: '1.05rem', textAlign: 'center' }}>
                {pendingExplore.explore.theme}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {pendingExplore.explore.choices.map(choice => (
                  <button
                    key={choice.id}
                    className="btn"
                    onClick={() => handleExploreChoice(choice.id)}
                    disabled={resolving}
                    style={{
                      textAlign: 'center',
                      padding: '1rem',
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      fontSize: '1rem',
                      userSelect: 'none',
                      WebkitUserSelect: 'none',
                    }}
                    onMouseOver={e => {
                      if (!resolving) e.target.style.background = 'rgba(255,255,255,0.1)'
                    }}
                    onMouseOut={e => {
                      if (!resolving) e.target.style.background = 'rgba(0,0,0,0.3)'
                    }}
                  >
                    <div style={{ color: 'var(--text-hi)' }}>
                      {choice.label}
                    </div>
                    {choice.hint && (
                      <div className="text-dim" style={{ fontSize: '0.8rem', marginTop: '0.3rem', fontStyle: 'italic' }}>
                        {choice.hint}
                      </div>
                    )}
                  </button>
                ))}
              </div>

              {resolving && (
                <div className="text-dim text-center" style={{ marginTop: '1rem' }}>
                  Resolving...
                </div>
              )}
              <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                <button className="btn" onClick={handleExit} disabled={resolving} style={{ padding: '0.5rem 1.5rem', fontSize: '0.9rem' }}>
                  Exit
                </button>
              </div>
            </div>
          )}

          {/* Battlefield UI */}
          {!postCombatPhase && !pendingEvent && !pendingExplore && (
            <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
              {lastResult && !lastResult.awaiting_choice && (() => {
                const teamResults = (lastResult?.combat?.team_results || lastResult?.team_results || []).filter(Boolean)
                if (teamResults.length > 1) {
                  const onArenaComplete = () => {
                    setArenasFinished(prev => {
                      const next = prev + 1
                      if (next >= teamResults.length) setPostCombatPhase(true)
                      return next
                    })
                  }
                  return (
                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                      {teamResults.map((tr, i) => (
                        <div key={i} style={{ flex: '1 1 480px', minWidth: '420px' }}>
                          <div style={{ textAlign: 'center', color: 'var(--text-hi)', fontFamily: 'Cinzel, serif', marginBottom: '0.3rem' }}>
                            Team {i + 1}
                          </div>
                          <CombatArena combatData={tr} onComplete={onArenaComplete} turnNarrations={turnNarrations[i]} />
                        </div>
                      ))}
                    </div>
                  )
                }
                return <CombatArena combatData={lastResult?.combat || lastResult} onComplete={() => setPostCombatPhase(true)} turnNarrations={turnNarrations[0]} />
              })()}
              <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                <button className="btn" onClick={handleExit} style={{ padding: '0.5rem 1.5rem', fontSize: '0.9rem' }}>
                  Exit
                </button>
              </div>
            </div>
          )}

          {/* Post Combat Screens */}
          {postCombatPhase && (
            <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
              <PostCombatScreen
                lastResult={lastResult}
                combatEntities={combatEntities}
                onReturn={handleExit}
                onRerun={handleRerun}
                busy={advancing}
              />

              {eventResolution && (
                <div className="card" style={{
                  marginTop: '2rem',
                  border: '1px solid var(--green)',
                  background: 'rgba(74,154,106,0.08)',
                  textAlign: 'center'
                }}>
                  <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.2rem', color: 'var(--green)', marginBottom: '0.5rem' }}>
                    {eventResolution.choice_label || 'Event Resolved'}
                  </div>
                  <div style={{ lineHeight: 1.6, fontSize: '1.05rem' }}>
                    {eventResolution.narrative}
                  </div>
                  {eventResolution.effects?.gems > 0 && (
                    <div style={{ marginTop: '1rem', fontSize: '1.1rem', color: '#00ffff' }}>
                      +{eventResolution.effects.gems} 💎
                    </div>
                  )}
                  {eventResolution.effects?.gold > 0 && (
                    <div className="text-gold" style={{ marginTop: '0.5rem', fontSize: '1.1rem' }}>
                      +{eventResolution.effects.gold}g
                    </div>
                  )}
                </div>
              )}

              {exploreResolution?.explore_loot && (
                <div className="card" style={{
                  marginTop: '2rem',
                  border: '1px solid var(--green)',
                  background: 'rgba(74,154,106,0.08)',
                  textAlign: 'center'
                }}>
                  <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.2rem', color: 'var(--green)', marginBottom: '0.5rem' }}>
                    Exploration Bonus
                  </div>
                  <div style={{ lineHeight: 1.6, fontSize: '1.05rem' }}>
                    {exploreResolution.explore_loot.summary}
                  </div>
                  {exploreResolution.explore_loot.loot?.desc && (
                    <div className="text-gold" style={{ marginTop: '1rem', fontSize: '1.1rem' }}>
                      {exploreResolution.explore_loot.loot.desc}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '1.5rem' }}>
          {/* Floor Grid */}
          <div className="card">
            <div className="text-gold" style={{ fontFamily: 'Cinzel, serif', marginBottom: '1rem', fontSize: '1.1rem' }}>
              Zone {selectedZone + 1} Floors
            </div>
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(5, 1fr)', 
              gap: '0.5rem' 
            }}>
              {Array.from({ length: 10 }).map((_, i) => {
                const floorNum = startFloorOfZone + i
                const isLocked = floorNum > highestFloor + 1
                const isNext = floorNum === highestFloor + 1
                const isSelected = floorNum === selectedFloor

                let bg = 'rgba(255,255,255,0.05)'
                let border = '1px solid rgba(255,255,255,0.1)'
                let color = 'var(--text-hi)'

                if (isLocked) {
                  bg = 'rgba(0,0,0,0.3)'
                  color = 'var(--text-dim)'
                } else if (isNext) {
                  border = '1px solid var(--gold)'
                }
                if (isSelected) {
                  bg = 'rgba(201, 168, 76, 0.2)'
                  border = '1px solid var(--gold)'
                }

                return (
                  <button
                    key={floorNum}
                    disabled={isLocked}
                    onClick={() => setSelectedFloor(floorNum)}
                    style={{
                      padding: '1rem',
                      background: bg,
                      border: border,
                      color: color,
                      borderRadius: '6px',
                      cursor: isLocked ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '0.25rem',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.2rem' }}>{floorNum}</div>
                    {isNext && <div style={{ fontSize: '0.7rem', color: 'var(--gold)', textTransform: 'uppercase' }}>Next</div>}
                    {!isLocked && !isNext && <div style={{ fontSize: '0.7rem', color: 'var(--green)', textTransform: 'uppercase' }}>Cleared</div>}
                    {floorNum % 10 === 0 && <div style={{ fontSize: '0.7rem', color: 'var(--red)', textTransform: 'uppercase' }}>Boss</div>}
                  </button>
                )
              })}
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1.5rem' }}>
              <button 
                className="btn" 
                disabled={selectedZone === 0}
                onClick={() => setSelectedZone(z => z - 1)}
              >
                ← Prev Zone
              </button>
              <button 
                className="btn" 
                disabled={selectedZone >= maxZone}
                onClick={() => setSelectedZone(z => z + 1)}
              >
                Next Zone →
              </button>
            </div>
          </div>

          {/* Deploy Panel */}
          <div className="card">
            <div className="text-gold" style={{ fontFamily: 'Cinzel, serif', marginBottom: '1rem', fontSize: '1.1rem' }}>
              Deploy
            </div>
            
            {Array.from({length: selectedFloor === 1 ? 1 : Math.floor((selectedFloor - 1) / 20) + 1}).map((_, idx) => (
              <div key={idx} style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
                <label className="text-dim text-sm" style={{ display: 'block', marginBottom: '0.5rem' }}>Select Team {idx + 1}</label>
                <select 
                  value={deployTeamIds[idx]}
                  onChange={e => {
                    const newIds = [...deployTeamIds]
                    newIds[idx] = parseInt(e.target.value)
                    setDeployTeamIds(newIds)
                  }}
                  style={{ width: '100%', background: 'var(--bg)', color: '#fff', border: '1px solid var(--border)', padding: '0.6rem 0.8rem', borderRadius: 4, fontFamily: 'inherit', fontSize: '0.9rem', marginBottom: '0.5rem' }}
                >
                  {[1,2,3,4,5,6,7,8,9,10].map(id => {
                    const count = team[id.toString()] ? team[id.toString()].length : 0
                    return <option key={id} value={id}>Team {id} ({count}/5)</option>
                  })}
                </select>
                
                {team[deployTeamIds[idx].toString()] && team[deployTeamIds[idx].toString()].length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                    {team[deployTeamIds[idx].toString()].map(h => (
                      <div key={h.id} style={{ display: 'flex', justifyContent: 'space-between', background: 'rgba(0,0,0,0.2)', padding: '0.3rem', borderRadius: 4 }}>
                        <span style={{ fontFamily: 'Cinzel, serif', fontSize: '0.8rem' }}>{h.name}</span>
                        <span className="text-dim" style={{ fontSize: '0.7rem' }}>Lv.{h.level}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-dim text-sm" style={{ fontStyle: 'italic' }}>
                    No heroes assigned to Team {deployTeamIds[idx]}.
                  </div>
                )}
              </div>
            ))}

            {floorPreview?.blurb && (
              <div style={{
                marginBottom: '1rem',
                padding: '0.6rem 0.8rem',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 6,
                fontSize: '0.85rem',
                fontStyle: 'italic',
                color: 'var(--text-hi)',
              }}>
                {floorPreview.blurb}
              </div>
            )}


            {error && <div className="text-red text-sm" style={{ marginBottom: '1rem' }}>{error}</div>}

            <div style={{ display: 'flex', gap: '0.6rem' }}>
              <button
                className="btn btn-primary"
                style={{ flex: 1, padding: '1rem', fontSize: '1.1rem' }}
                onClick={handleEnterFloor}
                disabled={advancing || deployTeamIds.slice(0, selectedFloor === 1 ? 1 : Math.floor((selectedFloor - 1) / 20) + 1).some(id => !team[id.toString()] || team[id.toString()].length === 0)}
              >
                {advancing ? 'Entering...' : `Enter Floor ${selectedFloor}`}
              </button>
              {selectedFloor <= highestFloor && (
                <button
                  className="btn"
                  style={{ padding: '1rem 1.2rem', fontSize: '1.1rem' }}
                  onClick={handleSkipFloor}
                  disabled={advancing || deployTeamIds.slice(0, selectedFloor === 1 ? 1 : Math.floor((selectedFloor - 1) / 20) + 1).some(id => !team[id.toString()] || team[id.toString()].length === 0)}
                  title="Re-run this already-cleared floor instantly for XP and gold, no animation"
                >
                  Rush
                </button>
              )}
            </div>
            <div className="text-dim text-sm" style={{ textAlign: 'center', marginTop: '0.5rem' }}>
              Cost: 2 Supplies 🍖
            </div>
          </div>
        </div>
      )}
      <FairyGuide floor={resolvedFloor || selectedFloor} lastResult={lastResult} fairyGender={base.fairy_gender} highestFloor={highestFloor} />
    </div>
  )
}
