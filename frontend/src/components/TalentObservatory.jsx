import React, { useState, useEffect } from 'react'
import { listHeroes, revealHeroTalent } from '../api/client'

// Talent Observatory: a paid, on-demand Talent reveal, separate from
// Archive's free per-level aptitude drip. The level of
// detail (tier/range/exact) is gated by this facility's own level.
export default function TalentObservatory({ upgrade, gold, onGoldChange, onUpgrade }) {
  const [heroes, setHeroes] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState('')
  const [revealing, setRevealing] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => { refresh() }, [])

  async function refresh() {
    setLoading(true)
    try {
      const all = await listHeroes(true)
      setHeroes(all)
    } catch (e) {
      setMsg(e.message)
    } finally {
      setLoading(false)
    }
  }

  const level = upgrade?.level || 0
  const maxLevel = upgrade?.max_level || 3
  const selected = heroes.find(h => h.id === parseInt(selectedId))
  const cost = selected ? (selected.current_star || selected.birth_star) * 500 : 0

  async function handleReveal() {
    if (!selected) return
    setRevealing(true)
    setMsg(null)
    try {
      const res = await revealHeroTalent(selected.id)
      setHeroes(prev => prev.map(h => h.id === selected.id ? { ...h, talent_reveal: res.talent_reveal } : h))
      if (onGoldChange) onGoldChange()
    } catch (e) {
      setMsg(e.message)
    } finally {
      setRevealing(false)
    }
  }

  return (
    <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
      <div style={{ width: '100%', aspectRatio: '3/1', overflow: 'hidden', position: 'relative' }}>
        <img src={`http://localhost:8000/static/facilities/mirror_of_fate.png`} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center', display: 'block' }} onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'none'; }} />
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to bottom, rgba(0,0,0,0) 50%, rgba(10,10,14,0.95) 100%)' }} />
      </div>
      <div style={{ padding: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h3 style={{ fontFamily: 'Cinzel, serif', color: 'var(--gold)', margin: 0 }}>Mirror of Fate (Lv.{level}/{maxLevel})</h3>
            </div>
            <div className="text-dim text-sm" style={{ marginTop: '0.2rem', lineHeight: 1.4 }}>
              Pay gold to instantly reveal a hero's hidden Talent.
              {level <= 1 && ' Reveals a vague tier (Poor/Average/Good/Exceptional).'}
              {level === 2 && ' Reveals a numeric range.'}
              {level >= 3 && ' Reveals the exact number.'}
            </div>
          </div>
          {level < maxLevel && (
            <button className="btn" style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem', alignSelf: 'flex-start' }} onClick={onUpgrade}>
              Upgrade ({upgrade?.next_cost ?? '?'}g)
            </button>
          )}
        </div>

        {msg && <div style={{ color: '#f87', fontSize: '0.85rem', marginBottom: '0.75rem' }}>{msg}</div>}

        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', alignItems: 'flex-start' }}>
          <select 
            value={selectedId} 
            onChange={e => setSelectedId(e.target.value)}
            className="input" 
            style={{ flex: 1 }}
          >
            <option value="">Select a hero to reveal...</option>
            {heroes.map(h => {
              const displayInfo = h.talent_reveal ? ` - ${h.talent_reveal}` : ' - Unrevealed'
              return <option key={h.id} value={h.id}>{h.name} ({h.class_name}){displayInfo}</option>
            })}
          </select>
          {selected && !selected.talent_reveal && (
             <button className="btn btn-gold" disabled={revealing || gold < cost} onClick={handleReveal}>
                {revealing ? 'Awakening...' : `Awaken (${cost}g)`}
             </button>
          )}
        </div>

        {selected && selected.talent_reveal && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            <div className="text-hi" style={{ fontFamily: 'Cinzel, serif' }}>{selected.name}</div>
            <div style={{ fontSize: '1.1rem', color: 'var(--gold)' }}>{selected.talent_reveal}</div>
            <div className="text-dim text-sm">Already revealed — frozen at the Mirror's level when revealed.</div>
          </div>
        )}
      </div>
    </div>
  )
}
