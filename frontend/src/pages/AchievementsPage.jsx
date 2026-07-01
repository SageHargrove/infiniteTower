import React, { useState, useEffect } from 'react'
import { getAchievements, claimAchievement } from '../api/client'

const CATEGORY_ORDER = ['Tower', 'Summoning', 'Roster', 'Combat', 'Economy', 'Equipment', 'Arena']

function rewardText(reward) {
  const parts = []
  if (reward.gems) parts.push(`💎 ${reward.gems}`)
  if (reward.gold) parts.push(`🪙 ${reward.gold}`)
  if (reward.summon_ticket) parts.push(`🎫 ${reward.summon_ticket}`)
  return parts.join('  ')
}

export default function AchievementsPage() {
  const [achievements, setAchievements] = useState(null)
  const [loading, setLoading] = useState(true)
  const [claiming, setClaiming] = useState(null)
  const [toast, setToast] = useState(null)

  useEffect(() => { refresh() }, [])

  async function refresh() {
    setLoading(true)
    try {
      const res = await getAchievements()
      setAchievements(res.achievements || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  async function handleClaim(id) {
    setClaiming(id)
    try {
      const res = await claimAchievement(id)
      setToast(`Claimed! ${rewardText(res.reward)}`)
      await refresh()
    } catch (e) {
      setToast(e.message)
    } finally {
      setClaiming(null)
      setTimeout(() => setToast(null), 3000)
    }
  }

  if (loading || !achievements) return <div className="page text-dim">Loading Achievements...</div>

  const claimedCount = achievements.filter(a => a.claimed).length
  const byCategory = {}
  for (const a of achievements) {
    if (!byCategory[a.category]) byCategory[a.category] = []
    byCategory[a.category].push(a)
  }

  return (
    <div className="page" style={{ maxWidth: '900px', margin: '0 auto' }}>
      <div className="section-header" style={{ marginBottom: '0.5rem', fontFamily: 'Cinzel, serif', fontSize: '2rem', textShadow: '0 0 10px rgba(255,255,255,0.2)' }}>
        Achievements
      </div>
      <div className="text-dim" style={{ marginBottom: '1.5rem' }}>
        {claimedCount} / {achievements.length} claimed
      </div>

      {toast && (
        <div style={{ position: 'fixed', top: '6rem', right: '2rem', background: 'rgba(0,0,0,0.9)', border: '1px solid var(--gold)', color: 'var(--gold)', padding: '0.8rem 1.2rem', borderRadius: 6, zIndex: 1000 }}>
          {toast}
        </div>
      )}

      {CATEGORY_ORDER.filter(c => byCategory[c]).map(category => (
        <div key={category} style={{ marginBottom: '2rem' }}>
          <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.3rem', color: 'var(--gold)', marginBottom: '0.8rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.4rem' }}>
            {category}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {byCategory[category].map(a => {
              const pct = Math.min(100, (a.progress / a.target) * 100)
              return (
                <div key={a.id} className="card" style={{
                  display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.9rem 1.2rem',
                  background: a.claimed ? 'rgba(255,255,255,0.02)' : a.complete ? 'rgba(201,168,76,0.1)' : 'rgba(0,0,0,0.4)',
                  border: `1px solid ${a.complete && !a.claimed ? 'var(--gold)' : 'var(--border)'}`,
                  opacity: a.claimed ? 0.55 : 1,
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 'bold', color: a.claimed ? 'var(--text-dim)' : 'var(--text-hi)' }}>
                      {a.name} {a.claimed && <span style={{ fontSize: '0.8rem' }}>✓</span>}
                    </div>
                    <div className="text-dim" style={{ fontSize: '0.85rem', marginBottom: '0.4rem' }}>{a.desc}</div>
                    <div style={{ background: 'rgba(255,255,255,0.08)', borderRadius: 4, height: '6px', overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: a.complete ? 'var(--gold)' : 'var(--green)', transition: 'width 0.3s' }} />
                    </div>
                    <div className="text-dim" style={{ fontSize: '0.75rem', marginTop: '0.2rem' }}>
                      {a.progress} / {a.target}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', minWidth: '140px' }}>
                    <div style={{ fontSize: '0.85rem', marginBottom: '0.4rem' }}>{rewardText(a.reward)}</div>
                    {a.claimed ? (
                      <span className="text-dim" style={{ fontSize: '0.85rem' }}>Claimed</span>
                    ) : a.complete ? (
                      <button className="btn btn-gold" disabled={claiming === a.id} onClick={() => handleClaim(a.id)}>
                        {claiming === a.id ? 'Claiming...' : 'Claim'}
                      </button>
                    ) : (
                      <span className="text-dim" style={{ fontSize: '0.85rem' }}>Locked</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
