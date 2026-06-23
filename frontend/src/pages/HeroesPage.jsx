import React, { useState, useEffect } from 'react'
import { listHeroes, setTeam, reorderTeam, dismissHero, dismissHeroesBulk, synthesizeHero, ascendHero, getAscensionInfo, promoteHero, regeneratePortraits, evolveHero, listEquipment, equipItem, unequipItem, egoAutoTeam, getEgoRecommendation, assignTeamLeader } from '../api/client'
import HeroCard from '../components/HeroCard'
import ClassEvolutionModal from '../components/ClassEvolutionModal'

export default function HeroesPage() {
  const [heroes, setHeroes] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [activeTab, setActiveTab] = useState('all') // 'all' | 1 | 2 | ... | 10
  const [assignTargetTeam, setAssignTargetTeam] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')
  
  const [starFilter, setStarFilter] = useState('any')
  const [classFilter, setClassFilter] = useState('any')
  const [sortBy, setSortBy] = useState('level')

  const [expandedId, setExpandedId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)
  const [egoPreview, setEgoPreview] = useState(null)
  const [eqModal, setEqModal] = useState(null)
  const [allEq, setAllEq] = useState([])
  const [evoModal, setEvoModal] = useState(null)

  // Synthesis state
  const [synthMode, setSynthMode] = useState(false)
  const [synthTarget, setSynthTarget] = useState(null)
  const [synthSacrifice, setSynthSacrifice] = useState(null)
  const [synthResult, setSynthResult] = useState(null)
  const [synthesizing, setSynthesizing] = useState(false)

  // Ascension & Promotion state
  const [ascending, setAscending] = useState(false)
  const [promoting, setPromoting] = useState(false)
  const [evolving, setEvolving] = useState(false)

  useEffect(() => { load() }, [])

  async function load() {
    const data = await listHeroes(true)
    setHeroes(data)
    try {
      const eqData = await listEquipment()
      setAllEq(eqData.unequipped || [])
    } catch(e) {}
  }

  function toggleSelect(id) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
    setMsg(null)
  }

  async function saveTeamFromAll() {
    setSaving(true)
    try {
      const currentTeam = heroes.filter(h => h.is_on_team === assignTargetTeam).map(h => h.id)
      const toAdd = Array.from(selected).filter(id => !currentTeam.includes(id))
      const nextTeam = [...currentTeam, ...toAdd]
      
      if (nextTeam.length > 5) {
        setMsg(`Cannot assign. Team ${assignTargetTeam} would exceed 5 heroes (currently ${currentTeam.length}, adding ${toAdd.length}).`)
        setSaving(false)
        return
      }
      
      await setTeam(assignTargetTeam, nextTeam)
      setMsg(`Added ${toAdd.length} heroes to Team ${assignTargetTeam}.`)
      setSelected(new Set())
      await load()
    } catch (e) {
      setMsg(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function removeFromTeam() {
    setSaving(true)
    try {
      const currentTeam = heroes.filter(h => h.is_on_team === activeTab).map(h => h.id)
      const nextTeam = currentTeam.filter(id => !selected.has(id))
      
      await setTeam(activeTab, nextTeam)
      setMsg(`Removed ${selected.size} heroes from Team ${activeTab}.`)
      setSelected(new Set())
      await load()
    } catch (e) {
      setMsg(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleDismiss(id, e) {
    e.stopPropagation()
    if (!confirm('Dismiss this hero permanently?')) return
    try {
      await dismissHero(id)
      setSelected(prev => { const n = new Set(prev); n.delete(id); return n })
      setMsg('Hero dismissed.')
      load()
    } catch (err) {
      setMsg(`Failed to dismiss: ${err.message}`)
      console.error('Dismiss failed:', err)
    }
  }

  // --- Dismiss Selected ---
  async function handleDismissSelected() {
    if (selected.size === 0) return
    
    // Check for high rank heroes
    const selectedHeroes = heroes.filter(h => selected.has(h.id))
    const highestStar = Math.max(...selectedHeroes.map(h => h.current_star || h.birth_star))
    
    if (highestStar >= 6) {
      if (!confirm(`CRITICAL WARNING: You have selected a ${highestStar}★ hero for dismissal! This action is PERMANENT. Are you absolutely sure?`)) return
    } else if (highestStar >= 4) {
      if (!confirm(`Warning: You have selected a high rank (${highestStar}★) hero for dismissal. Are you sure?`)) return
    } else {
      if (!confirm(`Dismiss ${selected.size} selected heroes permanently?`)) return
    }
    
    setSaving(true)
    try {
      const res = await dismissHeroesBulk(selectedHeroes.map(h => h.id))
      setMsg(`Dismissed ${res.deleted_count} heroes.`)
      setSelected(new Set())
      await load()
    } catch (e) {
      setMsg(`Bulk dismiss failed: ${e.message}`)
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  // --- Dismiss Filtered ---
  async function handleDismissFiltered() {
    if (displayHeroes.length === 0) return
    
    // Check for high rank heroes
    const highestStar = Math.max(...displayHeroes.map(h => h.current_star || h.birth_star))
    
    if (highestStar >= 6) {
      if (!confirm(`CRITICAL WARNING: The current filter includes a ${highestStar}★ hero! This action will dismiss ALL ${displayHeroes.length} heroes displayed. This is PERMANENT. Are you absolutely sure?`)) return
    } else if (highestStar >= 4) {
      if (!confirm(`Warning: The current filter includes a high rank (${highestStar}★) hero. Are you sure you want to dismiss ALL ${displayHeroes.length} displayed heroes?`)) return
    } else {
      if (!confirm(`Dismiss ALL ${displayHeroes.length} currently displayed heroes permanently?`)) return
    }
    
    setSaving(true)
    try {
      const res = await dismissHeroesBulk(displayHeroes.map(h => h.id))
      setMsg(`Dismissed ${res.deleted_count} heroes.`)
      setSelected(new Set())
      await load()
    } catch (e) {
      setMsg(`Bulk dismiss failed: ${e.message}`)
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  // --- Clear portrait cache ---
  async function handleClearCache() {
    if (!confirm('Clear all cached portraits? New ones will regenerate automatically.')) return
    try {
      const result = await regeneratePortraits()
      setMsg(result.message || 'Portrait cache cleared.')
    } catch (e) {
      setMsg(e.message)
    }
  }

  // --- Synthesis ---
  function enterSynthMode() {
    setSynthMode(true)
    setSynthTarget(null)
    setSynthSacrifice(null)
    setSynthResult(null)
    setExpandedId(null)
    setMsg(null)
  }

  function exitSynthMode() {
    setSynthMode(false)
    setSynthTarget(null)
    setSynthSacrifice(null)
    setSynthResult(null)
  }

  function handleSynthClick(heroId) {
    if (!synthTarget) {
      setSynthTarget(heroId)
      setSynthSacrifice(null)
    } else if (heroId === synthTarget) {
      setSynthTarget(null)
      setSynthSacrifice(null)
    } else if (!synthSacrifice) {
      setSynthSacrifice(heroId)
    } else if (heroId === synthSacrifice) {
      setSynthSacrifice(null)
    } else {
      setSynthSacrifice(heroId)
    }
  }

  async function executeSynthesis() {
    if (!synthTarget || !synthSacrifice) return
    setSynthesizing(true)
    setSynthResult(null)
    try {
      const result = await synthesizeHero(synthTarget, synthSacrifice)
      setSynthResult(result)
      setMsg(`Synthesis complete! ${result.message || ''}`)
      setSynthTarget(null)
      setSynthSacrifice(null)
      await load()
    } catch (e) {
      setMsg(e.message)
    } finally {
      setSynthesizing(false)
    }
  }

  // --- Ascension ---
  async function handleAscend(heroId, e) {
    e.stopPropagation()
    try {
      const info = await getAscensionInfo(heroId)
      const costStr = Object.entries(info.materials_required || {}).map(([m, q]) => `${q} ${m}`).join(', ')
      const pct = Math.round((info.fail_chance || 0) * 100)
      if (!confirm(`Ascend this hero? Costs ${costStr}.\nThis ritual has a ${pct}% chance to fail — materials are consumed either way.`)) return
    } catch (e) {
      // If the info lookup fails, fall through to attempting the ascend anyway — the
      // endpoint itself validates materials/level and will surface a clear error.
    }
    setAscending(true)
    try {
      const result = await ascendHero(heroId)
      if (result.failed) {
        setMsg(`Ascension failed! ${result.message || ''}`)
      } else {
        setMsg(`Ascension successful! ${result.message || ''}`)
      }
      await load()
    } catch (e) {
      setMsg(e.message)
    } finally {
      setAscending(false)
    }
  }



  async function handleAssignLeader(heroId, e) {
    e.stopPropagation()
    try {
      const result = await assignTeamLeader(heroId)
      setMsg(result.message || '')
      await load()
    } catch (e) {
      setMsg(e.message)
    }
  }

  // --- Drag and Drop ---
  const [draggedHeroId, setDraggedHeroId] = useState(null)
  const [dragOverHeroId, setDragOverHeroId] = useState(null)

  function handleDragStart(e, heroId) {
    if (activeTab === 'all' || synthMode) return;
    setDraggedHeroId(heroId);
  }

  function handleDragOver(e, heroId) {
    e.preventDefault();
    if (activeTab === 'all' || synthMode || heroId === draggedHeroId) return;
    setDragOverHeroId(heroId);
  }

  async function handleDrop(e, targetHeroId) {
    e.preventDefault();
    if (activeTab === 'all' || synthMode) return;
    if (draggedHeroId && draggedHeroId !== targetHeroId) {
      const currentTeam = [...displayHeroes];
      const draggedIdx = currentTeam.findIndex(h => h.id === draggedHeroId);
      const targetIdx = currentTeam.findIndex(h => h.id === targetHeroId);
      const [dragged] = currentTeam.splice(draggedIdx, 1);
      currentTeam.splice(targetIdx, 0, dragged);
      const newIds = currentTeam.map(h => h.id);
      
      try {
        await reorderTeam(activeTab, newIds);
        await load();
      } catch (e) {
        setMsg(e.message)
      }
    }
    setDraggedHeroId(null);
    setDragOverHeroId(null);
  }


  // --- Evolution ---
  async function handleEvolve(heroId, targetClass, e) {
    e.stopPropagation()
    if (!confirm(`Evolve to ${targetClass}? This change is permanent!`)) return
    setEvolving(true)
    try {
      const result = await evolveHero(heroId, targetClass)
      setMsg(`Hero evolved to ${result.new_class}!`)
      await load()
    } catch (e) {
      setMsg(e.message)
    } finally {
      setEvolving(false)
    }
  }

  const STAR_CAPS = { 1: 10, 2: 20, 3: 40, 4: 60, 5: 80, 6: 99, 7: 120 }

  const baseHeroes = heroes.filter(h => h.is_alive)
  
  // Filter by Tab
  let displayHeroes = baseHeroes
  if (activeTab !== 'all') {
    displayHeroes = displayHeroes.filter(h => h.is_on_team === activeTab)
  }
  
  // Apply visual filters
  if (starFilter !== 'any') {
    displayHeroes = displayHeroes.filter(h => (h.current_star || h.birth_star) === Number(starFilter))
  }
  if (classFilter !== 'any') {
    displayHeroes = displayHeroes.filter(h => h.hero_class === classFilter)
  }

  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase()
    displayHeroes = displayHeroes.filter(h => 
      h.name.toLowerCase().includes(q) || 
      h.hero_class.toLowerCase().includes(q) ||
      (h.synergy_group && h.synergy_group.toLowerCase().includes(q))
    )
  }

  // Sort
  if (activeTab !== 'all') {
    displayHeroes.sort((a, b) => (a.team_position || 0) - (b.team_position || 0))
  } else {
    displayHeroes.sort((a, b) => {
      if (sortBy === 'level') return b.level - a.level
      if (sortBy === 'rarity') return (b.current_star || b.birth_star) - (a.current_star || a.birth_star)
      if (sortBy === 'name') return a.name.localeCompare(b.name)
      return 0
    })
  }

  const unknownCount = heroes.filter(h => h.is_alive && (h.name || '').startsWith('Unknown')).length

  function getSynthBorderStyle(heroId) {
    if (!synthMode) return {}
    if (heroId === synthTarget) {
      return { outline: '2px solid var(--gold)', outlineOffset: '-2px', boxShadow: '0 0 12px rgba(201,168,76,0.4)' }
    }
    if (heroId === synthSacrifice) {
      return { outline: '2px solid var(--red)', outlineOffset: '-2px', boxShadow: '0 0 12px rgba(192,64,64,0.4)' }
    }
    return {}
  }
  const renderHeroCard = (hero, index) => {
    return (
      <div key={hero.id}
           style={{
             position: 'relative',
             width: '220px',
             height: '100%',
             display: 'flex',
             flexDirection: 'column',
             ...getSynthBorderStyle(hero.id),
             borderRadius: 6,
             cursor: activeTab !== 'all' && !synthMode && hero.condition !== 'Retired' ? 'grab' : 'pointer',
             opacity: hero.is_alive ? 1 : 0.6,
             filter: synthMode && !selectedForSynth.includes(hero.id) && !hero.is_on_team && hero.birth_star !== 7 ? 'grayscale(0.6)' : 'none',
             transform: dragOverHeroId === hero.id ? 'scale(1.05)' : 'scale(1)',
             transition: 'transform 0.1s ease',
             boxShadow: dragOverHeroId === hero.id ? '0 0 15px rgba(200,160,48,0.8)' : 'none'
           }}
           draggable={activeTab !== 'all' && !synthMode && hero.condition !== 'Retired'}
           onDragStart={(e) => handleDragStart(e, hero.id)}
           onDragOver={(e) => handleDragOver(e, hero.id)}
           onDrop={(e) => handleDrop(e, hero.id)}
           onDragEnd={() => { setDraggedHeroId(null); setDragOverHeroId(null); }}
      >
        {activeTab !== 'all' && (
          <div style={{
            position: 'absolute', top: -10, left: '50%', transform: 'translateX(-50%)',
            background: index < 2 ? 'rgba(201, 168, 76, 0.9)' : 'rgba(74, 154, 106, 0.9)',
            color: index < 2 ? '#000' : '#fff',
            padding: '2px 8px', borderRadius: 12, fontSize: '0.7rem',
            fontFamily: 'Cinzel, serif', fontWeight: 'bold', zIndex: 10,
            boxShadow: '0 2px 4px rgba(0,0,0,0.5)'
          }}>
            {index < 2 ? 'FRONTLINE' : 'BACKLINE'}
          </div>
        )}
        {hero.is_team_leader && (
          <div title="Team Leader" style={{
            position: 'absolute', top: -10, right: 8,
            background: 'rgba(201, 168, 76, 0.95)', color: '#000',
            padding: '2px 6px', borderRadius: 12, fontSize: '0.75rem',
            zIndex: 10, boxShadow: '0 0 8px rgba(201,168,76,0.6)'
          }}>
            👑
          </div>
        )}
        <HeroCard
          hero={hero}
          selected={!synthMode && selected.has(hero.id)}
          onClick={() => {
            if (synthMode) {
              if (hero.is_alive) handleSynthClick(hero.id)
              return
            }
            setExpandedId(hero.id)
          }}
          onToggleSelect={!synthMode ? () => toggleSelect(hero.id) : undefined}
          showFull={false}
          onRegenerateProfile={() => load()}
          onManageEquipment={(h, s, e) => setEqModal({ hero: h, slot: s, currentEq: e })}
          actions={!synthMode && hero.is_alive && (
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', alignItems: 'center' }}>
              {activeTab !== 'all' && (
                <button
                  className="btn"
                  style={{
                    border: hero.is_team_leader ? '1px solid var(--gold)' : '1px solid var(--border)',
                    color: hero.is_team_leader ? 'var(--gold)' : 'var(--text-dim)',
                    background: hero.is_team_leader ? 'rgba(201,168,76,0.15)' : 'transparent',
                    fontFamily: 'Cinzel, serif', padding: '0.3rem 0.7rem', fontSize: '0.72rem', borderRadius: 4
                  }}
                  onClick={(e) => handleAssignLeader(hero.id, e)}
                  title={hero.battle_tendency ? `Battle Tendency: ${hero.battle_tendency}` : undefined}
                >
                  👑 {hero.is_team_leader ? 'Leader' : 'Make Leader'}
                </button>
              )}
              {(hero.ascension_star || 0) < 7 && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                  <button className="btn" style={{ border: '1px solid var(--gold)', color: 'var(--gold)', background: 'rgba(201,168,76,0.1)', fontFamily: 'Cinzel, serif', padding: '0.3rem 0.8rem', fontSize: '0.75rem', borderRadius: 4 }} onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleAscend(hero.id, e); }} disabled={ascending || promoting || evolving}>
                    {ascending ? '...' : `◆ Ascend`}
                  </button>
                  <div className="text-dim" style={{ fontSize: '0.6rem', marginTop: '0.2rem' }}>Costs materials · risk of failure</div>
                </div>
              )}
              {hero.evolution_options?.length > 0 && (
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end', marginLeft: '1rem' }}>
                  <button className="btn" style={{ border: '1px solid #9d4edd', color: '#e0aaff', background: 'rgba(157, 78, 221, 0.1)', fontFamily: 'Cinzel, serif', padding: '0.4rem 1rem', fontSize: '0.85rem', borderRadius: 4, boxShadow: '0 0 8px rgba(157,78,221,0.5)' }} onClick={(e) => { e.preventDefault(); e.stopPropagation(); setEvoModal({ hero }); }} disabled={evolving || ascending || promoting}>
                    ✨ Class Advancement Available! ✨
                  </button>
                </div>
              )}
              {hero.level >= STAR_CAPS[hero.current_star || hero.birth_star] && (hero.current_star || hero.birth_star) < 7 && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                  <button className="btn" style={{ border: '1px solid var(--star5)', color: 'var(--star5)', background: 'rgba(201,168,76,0.1)', fontFamily: 'Cinzel, serif', padding: '0.3rem 0.8rem', fontSize: '0.75rem', boxShadow: '0 0 5px var(--star5)', borderRadius: 4 }} onClick={(e) => { e.preventDefault(); e.stopPropagation(); handlePromote(hero.id, e); }} disabled={ascending || promoting}>
                    {promoting ? '...' : `★ Promote`}
                  </button>
                  <div className="text-dim" style={{ fontSize: '0.6rem', marginTop: '0.2rem' }}>{(hero.current_star || hero.birth_star) * 5000} Gold · {(hero.current_star || hero.birth_star) * 10} Elemental Stones</div>
                </div>
              )}
            </div>
          )}
        />
        {/* Synthesis role labels */}
        {synthMode && hero.id === synthTarget && (
          <div style={{ position: 'absolute', top: 6, right: 8, color: 'var(--gold)', fontSize: '0.65rem', fontFamily: 'Cinzel, serif', background: 'rgba(0,0,0,0.7)', padding: '0.15rem 0.4rem', borderRadius: 2, zIndex: 10 }}>TARGET</div>
        )}
        {synthMode && hero.id === synthSacrifice && (
          <div style={{ position: 'absolute', top: 6, right: 8, color: 'var(--red)', fontSize: '0.65rem', fontFamily: 'Cinzel, serif', background: 'rgba(0,0,0,0.7)', padding: '0.15rem 0.4rem', borderRadius: 2, zIndex: 10 }}>SACRIFICE</div>
        )}
      </div>
    );
  };

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div className="section-header" style={{ marginBottom: 0 }}>
          Heroes — {heroes.length} alive
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {!synthMode ? (
            <button
              className="btn"
              onClick={enterSynthMode}
              style={{ padding: '0.3rem 0.8rem', fontSize: '0.72rem', border: '1px solid #8030c8', color: '#8030c8' }}
            >
              ⚗ Synthesis
            </button>
          ) : (
            <button className="btn btn-gold" onClick={exitSynthMode} style={{ padding: '0.3rem 0.8rem', fontSize: '0.72rem' }}>
              Cancel Synthesis
            </button>
          )}
        </div>
      </div>

      {expandedId && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.85)', zIndex: 100,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(5px)'
        }} onClick={() => setExpandedId(null)}>
          <div style={{ width: '1000px', maxWidth: '95vw', maxHeight: '90vh', overflowY: 'auto', borderRadius: '8px' }} onClick={e => e.stopPropagation()}>
            <HeroCard
              hero={heroes.find(h => h.id === expandedId)}
              showFull={true}
              onRegenerateProfile={() => load()}
              onManageEquipment={(h, s, e) => setEqModal({ hero: h, slot: s, currentEq: e })}
              actions={heroes.find(h => h.id === expandedId)?.is_alive && (
                <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', alignItems: 'center' }}>
                  {typeof activeTab === 'number' && heroes.find(h => h.id === expandedId)?.ego_type && (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.3rem' }}>
                      {egoPreview && egoPreview.heroId === expandedId && (
                        <div className="text-dim" style={{ fontSize: '0.7rem', textAlign: 'right', maxWidth: '260px' }}>
                          Wants: {egoPreview.recommended_team.map(h => h.name).join(', ')}
                        </div>
                      )}
                      <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <button className="btn" style={{ border: '1px solid #ff8888', color: '#ff8888', background: 'rgba(255,100,100,0.05)', fontFamily: 'Cinzel, serif', padding: '0.3rem 0.6rem', fontSize: '0.7rem', borderRadius: 4 }} onClick={async (e) => {
                          e.stopPropagation();
                          try {
                            const rec = await getEgoRecommendation(expandedId);
                            setEgoPreview({ heroId: expandedId, ...rec });
                          } catch (err) { setMsg(err.message) }
                        }}>
                          Preview Wishes
                        </button>
                        <button className="btn" style={{ border: '1px solid #ff8888', color: '#ff8888', background: 'rgba(255,100,100,0.1)', fontFamily: 'Cinzel, serif', padding: '0.3rem 0.8rem', fontSize: '0.75rem', borderRadius: 4 }} onClick={async (e) => {
                          e.stopPropagation();
                          try {
                            await egoAutoTeam(activeTab, expandedId);
                            await load();
                            setExpandedId(null);
                            setEgoPreview(null);
                          } catch (err) { setMsg(err.message) }
                        }}>
                          Let {heroes.find(h => h.id === expandedId)?.name} form Team {activeTab}
                        </button>
                      </div>
                    </div>
                  )}
                  {(heroes.find(h => h.id === expandedId)?.ascension_star || 0) < 7 && (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                      <button className="btn" style={{ border: '1px solid var(--gold)', color: 'var(--gold)', background: 'rgba(201,168,76,0.1)', fontFamily: 'Cinzel, serif', padding: '0.3rem 0.8rem', fontSize: '0.75rem', borderRadius: 4 }} onClick={(e) => handleAscend(expandedId, e)} disabled={ascending || promoting || evolving}>
                        {ascending ? '...' : `◆ Ascend`}
                      </button>
                      <div className="text-dim" style={{ fontSize: '0.6rem', marginTop: '0.2rem' }}>{(heroes.find(h => h.id === expandedId)?.birth_star || 1) * 1000} Gold</div>
                    </div>
                  )}
                  {heroes.find(h => h.id === expandedId)?.evolution_options?.length > 0 && (
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end', marginLeft: '1rem' }}>
                      <button className="btn" style={{ border: '1px solid #9d4edd', color: '#e0aaff', background: 'rgba(157, 78, 221, 0.1)', fontFamily: 'Cinzel, serif', padding: '0.4rem 1rem', fontSize: '0.85rem', borderRadius: 4, boxShadow: '0 0 8px rgba(157,78,221,0.5)' }} onClick={(e) => { e.preventDefault(); e.stopPropagation(); setEvoModal({ hero: heroes.find(h => h.id === expandedId) }); }} disabled={evolving || ascending || promoting}>
                        ✨ Class Advancement Available! ✨
                      </button>
                    </div>
                  )}
                  {heroes.find(h => h.id === expandedId)?.level >= STAR_CAPS[heroes.find(h => h.id === expandedId)?.current_star || heroes.find(h => h.id === expandedId)?.birth_star] && (heroes.find(h => h.id === expandedId)?.current_star || heroes.find(h => h.id === expandedId)?.birth_star) < 7 && (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                      <button className="btn" style={{ border: '1px solid var(--star5)', color: 'var(--star5)', background: 'rgba(201,168,76,0.1)', fontFamily: 'Cinzel, serif', padding: '0.3rem 0.8rem', fontSize: '0.75rem', boxShadow: '0 0 5px var(--star5)', borderRadius: 4 }} onClick={(e) => handlePromote(expandedId, e)} disabled={ascending || promoting}>
                        {promoting ? '...' : `★ Promote`}
                      </button>
                      <div className="text-dim" style={{ fontSize: '0.6rem', marginTop: '0.2rem' }}>{(heroes.find(h => h.id === expandedId)?.current_star || heroes.find(h => h.id === expandedId)?.birth_star) * 5000} Gold</div>
                    </div>
                  )}
                </div>
              )}
            />
          </div>
        </div>
      )}

      {!synthMode && (
        <div style={{ marginBottom: '1.5rem' }}>
          {/* Tabs */}
          <div style={{ display: 'flex', gap: '0.25rem', overflowX: 'auto', marginBottom: '1rem', paddingBottom: '0.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
            <button className={`btn ${activeTab === 'all' ? 'btn-gold' : ''}`} onClick={() => { setActiveTab('all'); setSelected(new Set()) }}>
              All Heroes
            </button>
            {[1, 2, 3, 4, 5].map(t => (
              <button key={t} className={`btn ${activeTab === t ? 'btn-gold' : ''}`} onClick={() => { setActiveTab(t); setSelected(new Set()) }}>
                Team {t}
              </button>
            ))}
          </div>

          {/* Filters & Actions */}
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap', background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: 4 }}>
            <input 
              type="text" 
              placeholder="Search Name, Class, or Synergy..." 
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{ background: 'var(--bg)', color: '#fff', border: '1px solid var(--border)', padding: '0.4rem 0.8rem', borderRadius: 4, minWidth: '220px' }}
            />
            <select value={starFilter} onChange={e => setStarFilter(e.target.value)} style={{ background: 'var(--bg)', color: '#fff', border: '1px solid var(--border)', padding: '0.4rem 0.8rem', borderRadius: 4 }}>
              <option value="any">Any Star</option>
              {[1, 2, 3, 4, 5, 6, 7].map(s => <option key={s} value={s}>{s} Star</option>)}
            </select>
            <select value={classFilter} onChange={e => setClassFilter(e.target.value)} style={{ background: 'var(--bg)', color: '#fff', border: '1px solid var(--border)', padding: '0.4rem 0.8rem', borderRadius: 4 }}>
              <option value="all">Any Class</option>
              {['Warrior', 'Mage', 'Rogue', 'Cleric', 'Archer', 'Paladin', 'Warlock', 'Bard', 'Druid', 'Monk', 'Ranger', 'Sorcerer', 'Necromancer', 'Assassin', 'Blacksmith', 'Thief', 'Classless'].map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <label className="text-dim" style={{ marginLeft: '0.5rem' }}>Sort by:</label>
              <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ background: 'var(--bg)', color: '#fff', border: '1px solid var(--border)', padding: '0.4rem 0.8rem', borderRadius: 4 }}>
                <option value="level">Level</option>
                <option value="stars">Star Rating</option>
                <option value="name">Name</option>
                <option value="health">Max Health</option>
                <option value="atk">Strength</option>
                <option value="def">Intelligence</option>
              </select>
            </div>

            {activeTab === 'all' ? (
              <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span className="text-dim text-sm">Assign {selected.size} heroes to:</span>
                <select value={assignTargetTeam} onChange={e => setAssignTargetTeam(Number(e.target.value))} style={{ background: 'var(--bg)', color: '#fff', border: '1px solid var(--gold)', padding: '0.4rem 0.8rem', borderRadius: 4 }}>
                  {[1, 2, 3, 4, 5].map(t => <option key={t} value={t}>Team {t}</option>)}
                </select>
                <button className="btn btn-primary" onClick={saveTeamFromAll} disabled={saving || selected.size === 0}>
                  {saving ? 'Assigning...' : 'Assign'}
                </button>
              </div>
            ) : (
              <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span className="text-dim text-sm">Team {activeTab} Members ({displayHeroes.length}/5)</span>
                <button className="btn btn-danger" onClick={removeFromTeam} disabled={saving || selected.size === 0}>
                  {saving ? 'Removing...' : `Remove Selected (${selected.size})`}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {msg && (
        <div className={`text-sm ${msg.includes('saved') || msg.includes('complete') || msg.includes('Added') || msg.includes('Removed') || msg.includes('successful') || msg.includes('Dismissed') || msg.includes('cleared') ? 'text-green' : 'text-red'}`}
             style={{ marginBottom: '1rem' }}>
          {msg}
        </div>
      )}

      {/* Synthesis mode instructions */}
      {synthMode && (
        <div className="card" style={{ marginBottom: '1rem', border: '1px solid #8030c8', background: 'rgba(128,48,200,0.08)', padding: '0.75rem 1rem' }}>
          <div style={{ fontFamily: 'Cinzel, serif', fontSize: '0.85rem', color: '#8030c8', marginBottom: '0.4rem' }}>
            ⚗ Synthesis Mode
          </div>
          <div className="text-sm" style={{ lineHeight: 1.6 }}>
            {!synthTarget && !synthSacrifice && (
              <span className="text-dim">Step 1: Click a hero to select as the <span className="text-gold">target</span> (receives the bonus).</span>
            )}
            {synthTarget && !synthSacrifice && (
              <span className="text-dim">Step 2: Click another hero to select as the <span className="text-red">sacrifice</span> (will be consumed).</span>
            )}
            {synthTarget && synthSacrifice && (
              <span>Ready! <span className="text-gold">Target</span> selected, <span className="text-red">sacrifice</span> selected.</span>
            )}
          </div>
          {synthTarget && synthSacrifice && (
            <button className="btn btn-primary" onClick={executeSynthesis} disabled={synthesizing} style={{ marginTop: '0.6rem' }}>
              {synthesizing ? 'Synthesizing...' : '⚗ Execute Synthesis'}
            </button>
          )}
        </div>
      )}

      {/* Synthesis result */}
      {synthResult && (
        <div className="card" style={{ marginBottom: '1rem', border: '1px solid var(--green)', background: 'rgba(74,154,106,0.08)', padding: '0.75rem 1rem' }}>
          <div style={{ fontFamily: 'Cinzel, serif', fontSize: '0.85rem', color: 'var(--green)', marginBottom: '0.3rem' }}>Synthesis Complete</div>
          <div className="text-sm" style={{ lineHeight: 1.5 }}>{synthResult.message || 'The sacrifice has been consumed. Target hero empowered.'}</div>
          {synthResult.xp_gained != null && <div className="text-gold text-sm" style={{ marginTop: '0.3rem' }}>+{synthResult.xp_gained} XP gained</div>}
        </div>
      )}



      {activeTab !== 'all' && !synthMode && displayHeroes.length > 0 && (
        <div className="text-gold" style={{ background: 'rgba(201,168,76,0.1)', border: '1px solid var(--gold-dim)', padding: '0.75rem', borderRadius: 4, marginBottom: '1rem', textAlign: 'center', fontFamily: 'Cinzel, serif' }}>
          ✥ Drag and drop hero cards to rearrange your Frontline and Backline! ✥
        </div>
      )}

      {activeTab === 'all' || synthMode ? (
        <div className="hero-grid">
          {displayHeroes.length === 0 && activeTab !== 'all' && (
            <div className="text-dim" style={{ padding: '2rem', fontStyle: 'italic', gridColumn: '1 / -1', textAlign: 'center' }}>
              No heroes on Team {activeTab}.<br/>
              To add heroes, switch to the "All" tab, click the checkmarks on your desired heroes, and use the "Assign" button at the top right.
            </div>
          )}
          {displayHeroes.length === 0 && activeTab === 'all' && (
            <div className="text-dim" style={{ padding: '2rem 0' }}>
              No heroes found for the current filter.
            </div>
          )}
          {displayHeroes.map((hero, index) => renderHeroCard(hero, index))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', alignItems: 'center', marginTop: '1rem' }}>
          {displayHeroes.length === 0 && (
            <div className="text-dim" style={{ padding: '2rem', fontStyle: 'italic', textAlign: 'center' }}>
              No heroes on Team {activeTab}.<br/>
              To add heroes, switch to the "All" tab, click the checkmarks on your desired heroes, and use the "Assign" button at the top right.
            </div>
          )}
          
          {/* Frontline */}
          {displayHeroes.length > 0 && (
            <div style={{ display: 'flex', gap: '2rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              {displayHeroes.slice(0, 2).map((hero, i) => renderHeroCard(hero, i))}
            </div>
          )}
          
          {/* Backline */}
          {displayHeroes.length > 2 && (
            <div style={{ display: 'flex', gap: '2rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              {displayHeroes.slice(2, 5).map((hero, i) => renderHeroCard(hero, i + 2))}
            </div>
          )}
        </div>
      )}

      {/* Roster Management */}
      {!synthMode && (
        <div style={{ marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
          <div className="section-header">Roster Management</div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button className="btn btn-danger" onClick={handleDismissSelected} disabled={selected.size === 0 || saving} style={{ fontSize: '0.72rem' }}>
              ✕ Dismiss Selected ({selected.size})
            </button>
            <button className="btn btn-danger" onClick={handleDismissFiltered} disabled={displayHeroes.length === 0 || saving} style={{ fontSize: '0.72rem' }}>
              ✕ Dismiss All Filtered ({displayHeroes.length})
            </button>
            <button className="btn" onClick={handleClearCache} style={{ fontSize: '0.72rem', border: '1px solid var(--blue)', color: 'var(--blue)' }}>
              🔄 Clear Portrait Cache
            </button>
          </div>
          <div className="text-dim text-sm" style={{ marginTop: '0.5rem' }}>
            Select heroes by clicking them, then dismiss them in bulk.
            "Clear Portrait Cache" deletes old cached portraits — new diverse ones regenerate automatically.
          </div>
        </div>
      )}

      {/* Equipment Modal */}
      {eqModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.85)', zIndex: 200,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(5px)'
        }} onClick={() => setEqModal(null)}>
          <div className="card" style={{ width: '500px', maxWidth: '90vw', maxHeight: '80vh', overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontFamily: 'Cinzel, serif', color: 'var(--gold)', marginBottom: '1rem', textTransform: 'capitalize' }}>
              Manage {eqModal.slot} for {eqModal.hero.name}
            </h3>
            
            {eqModal.currentEq && (
              <div style={{ marginBottom: '1.5rem', padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: 4, border: '1px solid var(--border)' }}>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.8rem', marginBottom: '0.5rem' }}>Currently Equipped:</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ color: 'var(--gold)', fontFamily: 'Cinzel, serif' }}>{eqModal.currentEq.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Rarity: {eqModal.currentEq.rarity}</div>
                  </div>
                  <button className="btn btn-danger" onClick={async () => {
                    await unequipItem(eqModal.currentEq.id);
                    setEqModal(null);
                    load();
                  }}>Unequip</button>
                </div>
              </div>
            )}

            <div style={{ color: 'var(--text-dim)', fontSize: '0.8rem', marginBottom: '0.5rem' }}>Available {eqModal.slot}s in Storage:</div>
            {allEq.filter(e => e.type?.toLowerCase() === eqModal.slot).length === 0 ? (
              <div className="text-dim text-sm" style={{ fontStyle: 'italic' }}>No unequipped {eqModal.slot}s available.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '300px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                {allEq.filter(e => e.type?.toLowerCase() === eqModal.slot)
                  .sort((a, b) => {
                    const tiers = ["F-", "F", "F+", "E-", "E", "E+", "D-", "D", "D+", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+", "S-", "S", "S+", "SS", "SSS", "Z"];
                    return tiers.indexOf(b.rarity) - tiers.indexOf(a.rarity);
                  })
                  .map(eq => (
                  <div key={eq.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', borderRadius: 4 }}>
                    <div>
                      <div style={{ color: 'var(--text-hi)', fontFamily: 'Cinzel, serif' }}>{eq.name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        Rarity: {eq.rarity} | Level: {eq.level} | {eq.base_str > 0 && `STR +${eq.base_str} `}{eq.base_int > 0 && `INT +${eq.base_int} `}{eq.base_hlt > 0 && `Health +${eq.base_hlt} `}{eq.base_agi > 0 && `AGI +${eq.base_agi} `}{eq.str_pct > 0 && `STR +${(eq.str_pct*100).toFixed(0)}% `}{eq.int_pct > 0 && `INT +${(eq.int_pct*100).toFixed(0)}% `}{eq.hlt_pct > 0 && `Health +${(eq.hlt_pct*100).toFixed(0)}% `}{eq.agi_pct > 0 && `AGI +${(eq.agi_pct*100).toFixed(0)}% `}{eq.crit_chance > 0 && `Crit +${(eq.crit_chance*100).toFixed(0)}% `}{eq.dodge_chance > 0 && `Dodge +${(eq.dodge_chance*100).toFixed(0)}% `}{eq.armor_pen > 0 && `ArmorPen +${(eq.armor_pen*100).toFixed(0)}%`}
                      </div>
                    </div>
                    <button className="btn btn-primary" onClick={async () => {
                      await equipItem(eq.id, eqModal.hero.id);
                      setEqModal(null);
                      load();
                    }}>Equip</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Evolution Modal */}
      {evoModal && (
        <ClassEvolutionModal 
          hero={evoModal.hero} 
          onClose={() => setEvoModal(null)}
          onEvolve={(newClass) => {
            setMsg(`Hero evolved to ${newClass}!`)
            load()
          }}
        />
      )}
    </div>
  )
}

