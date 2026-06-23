import React, { useState, useEffect } from 'react'
import { pullHeroes, getOdds, getBase, getPityInfo, redeemSpark, pullEquipment } from '../api/client'
import HeroCard from '../components/HeroCard'
import SummoningOverlay from '../components/SummoningOverlay'

export default function SummonPage({ onGoldChange }) {
  const [gold, setGold] = useState(0)
  const [gems, setGems] = useState(0)
  const [odds, setOdds] = useState(null)
  const [pityInfo, setPityInfo] = useState(null)
  const [pulling, setPulling] = useState(false)
  const [redeeming, setRedeeming] = useState(false)
  const [results, setResults] = useState([])
  const [error, setError] = useState(null)
  const [usePortrait, setUsePortrait] = useState(true)
  const [expandedId, setExpandedId] = useState(null)
  const [showAnimation, setShowAnimation] = useState(false)

  useEffect(() => {
    refreshData()
  }, [])

  async function refreshData() {
    getBase().then(b => { setGold(b.gold); setGems(b.gems || 0); })
    getOdds().then(setOdds)
    getPityInfo().then(setPityInfo)
  }

  async function doPull(count) {
    setPulling(true)
    setError(null)
    setResults([])
    try {
      const data = await pullHeroes(count, usePortrait)
      setResults(data.pulled)
      const cost = count * 100
      setGems(g => g - cost)
      setShowAnimation(true)
      await refreshData()
      if (onGoldChange) onGoldChange()
    } catch (e) {
      setError(e.message)
    } finally {
      setPulling(false)
    }
  }

  async function doPullEquipment(count) {
    setPulling(true)
    setError(null)
    setResults([])
    try {
      const data = await pullEquipment(count)
      setResults(data.results.map(e => ({...e, is_equipment: true})))
      const cost = count * 500
      setGold(g => g - cost)
      // setShowAnimation(true) // We can use the same or a different animation later, for now just show results
      await refreshData()
      if (onGoldChange) onGoldChange()
    } catch (e) {
      setError(e.message)
    } finally {
      setPulling(false)
    }
  }

  async function doSpark() {
    if (!confirm('Redeem 100 sparks for a guaranteed 5★ hero?')) return
    setRedeeming(true)
    setError(null)
    try {
      const data = await redeemSpark()
      setResults([data.hero])
      await refreshData()
    } catch (e) {
      setError(e.message)
    } finally {
      setRedeeming(false)
    }
  }

  return (
    <div className="page">
      {showAnimation && results.length > 0 && (
        <SummoningOverlay 
          results={results} 
          onComplete={() => setShowAnimation(false)} 
        />
      )}
      
      {!showAnimation && (
        <>
          <div className="section-header">Summoning Gate</div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '800px', margin: '0 auto' }}>
        
        {/* Pull panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          <div style={{ marginBottom: '0.5rem', textAlign: 'center' }}>
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={usePortrait}
                onChange={e => setUsePortrait(e.target.checked)}
                style={{ transform: 'scale(1.2)' }}
              />
              <span className="text-dim">Generate portrait (uses DALL-E API)</span>
            </label>
          </div>

          <div style={{ display: 'flex', gap: '1.5rem' }}>
            <button 
              className="btn btn-gold" 
              onClick={() => doPull(1)} 
              disabled={pulling || gems < 100}
              style={{ flex: 1, padding: '2rem', fontSize: '1.6rem', fontFamily: 'Cinzel, serif', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem', border: '2px solid var(--gold)', borderRadius: 8, background: 'rgba(201,168,76,0.1)' }}
            >
              <div>{pulling ? 'Summoning...' : 'Summon 1x'}</div>
              <div style={{ fontSize: '1rem', color: '#fff', opacity: 0.8, letterSpacing: '2px' }}>100 GEMS 💎</div>
            </button>

            <button 
              className="btn btn-gold" 
              onClick={() => doPull(10)} 
              disabled={pulling || gems < 1000}
              style={{ flex: 1, padding: '2rem', fontSize: '1.6rem', fontFamily: 'Cinzel, serif', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem', border: '2px solid var(--gold)', borderRadius: 8, background: 'rgba(201,168,76,0.15)', boxShadow: '0 0 20px rgba(201,168,76,0.3)' }}
            >
              <div>{pulling ? 'Summoning...' : 'Summon 10x'}</div>
              <div style={{ fontSize: '1rem', color: '#fff', opacity: 0.8, letterSpacing: '2px' }}>1000 GEMS 💎</div>
            </button>
          </div>

          <div style={{ display: 'flex', gap: '1.5rem', marginTop: '1rem' }}>
            <button 
              className="btn btn-gold" 
              onClick={() => doPullEquipment(1)} 
              disabled={pulling || gold < 500}
              style={{ flex: 1, padding: '2rem', fontSize: '1.6rem', fontFamily: 'Cinzel, serif', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem', border: '2px solid var(--star1)', borderRadius: 8, background: 'rgba(150,150,150,0.1)' }}
            >
              <div>{pulling ? 'Summoning...' : 'Equip Summon 1x'}</div>
              <div style={{ fontSize: '1rem', color: '#fff', opacity: 0.8, letterSpacing: '2px' }}>500 GOLD 💰</div>
            </button>

            <button 
              className="btn btn-gold" 
              onClick={() => doPullEquipment(10)} 
              disabled={pulling || gold < 5000}
              style={{ flex: 1, padding: '2rem', fontSize: '1.6rem', fontFamily: 'Cinzel, serif', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem', border: '2px solid var(--star1)', borderRadius: 8, background: 'rgba(150,150,150,0.15)', boxShadow: '0 0 20px rgba(150,150,150,0.3)' }}
            >
              <div>{pulling ? 'Summoning...' : 'Equip Summon 10x'}</div>
              <div style={{ fontSize: '1rem', color: '#fff', opacity: 0.8, letterSpacing: '2px' }}>5000 GOLD 💰</div>
            </button>
          </div>

          {error && (
            <div className="text-red text-center" style={{ marginTop: '0.5rem', fontSize: '1.1rem' }}>{error}</div>
          )}
        </div>

        {/* Odds table & Pity */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
          {odds && (
            <div className="card">
              <div className="section-header" style={{ marginBottom: '1rem', textAlign: 'center' }}>Pull Rates</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {Object.entries(odds).map(([star, data]) => {
                  const numStar = Number(star);
                  const isRainbow = numStar === 7;
                  return (
                    <div key={star} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1.1rem', padding: '0.4rem 1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'rgba(0,0,0,0.2)', borderRadius: 4 }}>
                      <span className={isRainbow ? 'rainbow-text' : `birth-star-${star}`} style={{ color: isRainbow ? undefined : `var(--star${star})`, textShadow: numStar >= 5 ? '0 0 5px currentColor' : 'none' }}>
                        {'★'.repeat(numStar)}
                      </span>
                      <span className="text-dim" style={{ fontFamily: 'monospace', fontSize: '1.1rem' }}>
                        {Number(data.percent).toFixed(2)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {pityInfo && (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div className="section-header" style={{ marginBottom: '1rem', textAlign: 'center' }}>Sparks</div>

                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '0.8rem' }}>
                    <div className="text-dim" style={{ fontSize: '1.1rem' }}>Sparks</div>
                    <div style={{ fontSize: '1.5rem', color: 'var(--star5)', fontFamily: 'Cinzel, serif' }}>
                      {pityInfo.spark_points} <span className="text-dim" style={{ fontSize: '1rem' }}>/ 100</span>
                    </div>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: 'var(--bg)', borderRadius: '4px', overflow: 'hidden', marginBottom: '1.5rem', border: '1px solid var(--border)' }}>
                    <div style={{ 
                      height: '100%', 
                      width: `${Math.min(100, (pityInfo.spark_points / 100) * 100)}%`, 
                      background: 'var(--star5)',
                      boxShadow: '0 0 10px var(--star5)',
                      transition: 'width 0.5s ease-out'
                    }} />
                  </div>
                  
                  <button 
                    className="btn" 
                    style={{ width: '100%', padding: '1rem', fontSize: '1.1rem', background: pityInfo.spark_points >= 100 ? 'rgba(201, 168, 76, 0.2)' : 'rgba(255,255,255,0.05)', color: pityInfo.spark_points >= 100 ? 'var(--star5)' : 'var(--text-dim)', border: `2px solid ${pityInfo.spark_points >= 100 ? 'var(--star5)' : 'var(--border)'}`, boxShadow: pityInfo.spark_points >= 100 ? '0 0 15px rgba(201,168,76,0.3)' : 'none' }}
                    onClick={doSpark}
                    disabled={redeeming || pulling || pityInfo.spark_points < 100}
                  >
                    {redeeming ? 'Redeeming...' : 'Redeem 5★ (100 Sparks)'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div style={{ marginTop: '2rem' }}>
          <div className="section-header">Summoned</div>
          <div className="hero-grid">
            {results.map((item, idx) => {
              if (item.is_equipment) {
                return (
                  <div key={idx} className="card" style={{ border: '1px solid var(--border)', textAlign: 'center', padding: '1.5rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>
                      {item.type === 'Weapon' ? '⚔️' : item.type === 'Armor' ? '🛡️' : '💍'}
                    </div>
                    <div style={{ fontSize: '1.2rem', fontFamily: 'Cinzel, serif', fontWeight: 'bold' }}>{item.name}</div>
                    <div style={{ fontSize: '1rem', marginTop: '0.5rem', color: 'var(--star5)' }}>{item.rarity} Rank</div>
                  </div>
                )
              }
              return <HeroCard key={item.id} hero={item} onClick={() => setExpandedId(item.id)} />
            })}
          </div>
        </div>
      )}

      {expandedId && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.85)', zIndex: 100,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(5px)'
        }} onClick={() => setExpandedId(null)}>
          <div style={{ width: '1000px', maxWidth: '95vw', maxHeight: '90vh', overflowY: 'auto', borderRadius: '8px' }} onClick={e => e.stopPropagation()}>
            <HeroCard
              hero={results.find(h => h.id === expandedId)}
              showFull={true}
            />
          </div>
        </div>
      )}
        </>
      )}
    </div>
  )
}
