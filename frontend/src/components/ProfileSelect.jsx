import React, { useState, useEffect } from 'react'
import { listProfiles, switchProfile, renameProfile, deleteProfile } from '../api/client'

const DIFFICULTY_OPTIONS = [
  { id: 'easy', label: 'Easy', desc: 'Weaker enemies, +25% gold. Rare drops are less common.', note: 'Easy mode profiles are not eligible for leaderboard rankings.' },
  { id: 'normal', label: 'Normal', desc: 'The baseline experience.', note: null },
  { id: 'hard', label: 'Hard', desc: 'Stronger enemies, better rare drops. Gold stays at baseline.', note: 'Hard mode: full leaderboard access, separate prestige tier.' },
]

export default function ProfileSelect({ onSelect }) {
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [newProfile, setNewProfile] = useState('')
  const [selectedProfile, setSelectedProfile] = useState(null)
  const [msg, setMsg] = useState(null)
  // Difficulty is locked in at creation — see backend/services/difficulty_service.py
  const [pendingNewName, setPendingNewName] = useState(null)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const data = await listProfiles()
      setProfiles(data.profiles)
      if (selectedProfile && !data.profiles.includes(selectedProfile)) setSelectedProfile(null)
    } catch (e) {
      setMsg(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleLoadSelected() {
    if (!selectedProfile) return
    try {
      setLoading(true)
      await switchProfile(selectedProfile)
      onSelect(selectedProfile)
    } catch (e) { setMsg(e.message); setLoading(false) }
  }

  function handleCreate(e) {
    e.preventDefault()
    const name = newProfile.trim()
    if (!name) return
    setPendingNewName(name)
  }

  async function confirmCreate(difficulty) {
    const name = pendingNewName
    setPendingNewName(null)
    try {
      setLoading(true)
      await switchProfile(name, difficulty)
      onSelect(name)
    } catch (e) { setMsg(e.message); setLoading(false) }
  }

  async function handleRename() {
    if (!selectedProfile) return
    const newName = prompt(`Rename "${selectedProfile}" to:`, selectedProfile)
    if (!newName || newName === selectedProfile) return
    try {
      setLoading(true)
      await renameProfile(selectedProfile, newName)
      setSelectedProfile(newName)
      await load()
      setMsg(`Renamed to ${newName}`)
    } catch(e) { setMsg(e.message); setLoading(false) }
  }

  async function handleDelete() {
    if (!selectedProfile) return
    if (!window.confirm(`Permanently delete "${selectedProfile}"?`)) return
    try {
      setLoading(true)
      await deleteProfile(selectedProfile)
      setSelectedProfile(null)
      await load()
      setMsg('Profile deleted.')
    } catch(e) { setMsg(e.message); setLoading(false) }
  }

  if (loading && profiles.length === 0) return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000', color: '#fff', fontFamily: 'Cinzel, serif' }}>
      Loading...
    </div>
  )

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative', overflow: 'hidden', background: '#000' }}>

      {/* Tower art is a tall portrait image (341x1024) — `cover` on a wide
          landscape window forces it to scale by its WORST-matching
          dimension (width), blowing it up ~6x and showing only a tight
          sliver of it. `contain` shows the whole image at its natural
          scale instead, anchored to the right where the panel isn't. */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: 'url(/tower_wide.png)',
        backgroundSize: 'cover',
        backgroundPosition: 'center center',
        backgroundRepeat: 'no-repeat',
      }} />

      {/* Left vignette — makes panel readable, right half stays fully visible */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(to right, rgba(5,5,10,0.95) 0%, rgba(5,5,10,0.82) 28%, rgba(5,5,10,0.2) 55%, transparent 75%)',
      }} />
      {/* Bottom depth vignette */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(to top, rgba(5,5,10,0.65) 0%, transparent 45%)',
      }} />

      {/* ── Left panel ── */}
      <div style={{
        position: 'absolute', left: 0, top: 0, bottom: 0,
        width: '360px',
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '3rem 2.5rem',
        zIndex: 1,
      }}>

        {/* Title */}
        <div style={{ marginBottom: '2.5rem' }}>
          <div style={{
            fontSize: '0.65rem', letterSpacing: '5px',
            color: 'rgba(201,168,76,0.75)', marginBottom: '0.6rem',
            fontFamily: 'Cinzel, serif',
          }}>ENTER THE</div>
          <h1 style={{
            fontFamily: 'Cinzel, serif', fontSize: '2.5rem', fontWeight: 'bold',
            color: '#fff', margin: 0, lineHeight: 1.15,
            textShadow: '0 0 40px rgba(120,140,255,0.5), 0 2px 10px rgba(0,0,0,1)',
          }}>
            Tower of<br />Eternity
          </h1>
        </div>

        {/* Glassmorphism card */}
        <div style={{
          background: 'rgba(8,8,18,0.65)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          border: '1px solid rgba(201,168,76,0.18)',
          borderRadius: '14px',
          padding: '1.5rem',
          boxShadow: '0 8px 40px rgba(0,0,0,0.5)',
        }}>
          {msg && <div style={{ color: '#f87', fontSize: '0.8rem', marginBottom: '0.75rem', textAlign: 'center' }}>{msg}</div>}

          {/* New profile */}
          <form onSubmit={handleCreate} style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.2rem', paddingBottom: '1.2rem', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
            <input
              type="text"
              placeholder="New profile name..."
              value={newProfile}
              onChange={e => setNewProfile(e.target.value)}
              style={{
                flex: 1, minWidth: 0, background: 'rgba(0,0,0,0.45)',
                border: '1px solid rgba(255,255,255,0.12)',
                padding: '0.5rem 0.75rem', color: '#fff',
                borderRadius: 7, fontSize: '0.88rem', outline: 'none',
              }}
            />
            <button type="submit" className="btn btn-gold" disabled={!newProfile.trim()} style={{ padding: '0.5rem 0.9rem', fontSize: '0.82rem' }}>
              Create
            </button>
          </form>

          {/* Save list */}
          <div style={{ fontSize: '0.62rem', letterSpacing: '3px', color: 'rgba(255,255,255,0.35)', marginBottom: '0.5rem', fontFamily: 'Cinzel, serif' }}>
            SAVE FILES
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginBottom: '1.2rem', maxHeight: '26vh', overflowY: 'auto' }}>
            {profiles.length === 0 && (
              <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: '0.85rem', fontStyle: 'italic' }}>No profiles yet.</div>
            )}
            {profiles.map(p => {
              const sel = selectedProfile === p
              return (
                <button
                  key={p}
                  onClick={() => setSelectedProfile(p)}
                  style={{
                    padding: '0.6rem 0.9rem',
                    background: sel ? 'rgba(201,168,76,0.12)' : 'rgba(255,255,255,0.03)',
                    border: sel ? '1px solid rgba(201,168,76,0.55)' : '1px solid rgba(255,255,255,0.07)',
                    borderRadius: 7, cursor: 'pointer', transition: 'all 0.15s',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    color: sel ? 'var(--gold)' : '#ccc',
                  }}
                >
                  <span style={{ fontFamily: 'Cinzel, serif', fontWeight: 'bold', fontSize: '0.92rem' }}>{p}</span>
                  {sel && <span style={{ fontSize: '0.65rem', opacity: 0.8 }}>✓</span>}
                </button>
              )
            })}
          </div>

          {/* Actions */}
          <div style={{
            display: 'flex', gap: '0.4rem',
            opacity: selectedProfile ? 1 : 0.25,
            pointerEvents: selectedProfile ? 'auto' : 'none',
            transition: 'opacity 0.2s',
          }}>
            <button
              className="btn btn-gold"
              style={{ flex: 2, padding: '0.6rem', fontWeight: 'bold', fontSize: '0.88rem', letterSpacing: '1px' }}
              onClick={handleLoadSelected}
            >
              Enter Tower
            </button>
            <button className="btn" style={{ flex: 1, padding: '0.6rem', fontSize: '0.78rem' }} onClick={handleRename}>
              Rename
            </button>
            <button
              className="btn"
              style={{ flex: 1, padding: '0.6rem', fontSize: '0.78rem', background: 'rgba(150,0,0,0.15)', border: '1px solid rgba(255,60,60,0.2)', color: '#f88' }}
              onClick={handleDelete}
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      {pendingNewName && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 50,
          background: 'rgba(0,0,0,0.75)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            background: 'rgba(10,10,18,0.95)', border: '1px solid rgba(201,168,76,0.3)',
            borderRadius: 14, padding: '2rem', width: '420px', maxWidth: '90vw',
            boxShadow: '0 8px 50px rgba(0,0,0,0.7)',
          }}>
            <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.3rem', color: 'var(--gold)', marginBottom: '0.4rem', textAlign: 'center' }}>
              Choose Your Difficulty
            </div>
            <div style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.5)', textAlign: 'center', marginBottom: '1.4rem' }}>
              "{pendingNewName}" — this cannot be changed later.
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {DIFFICULTY_OPTIONS.map(opt => (
                <button
                  key={opt.id}
                  className="btn"
                  style={{ textAlign: 'left', padding: '0.75rem 0.9rem', borderRadius: 8 }}
                  onClick={() => confirmCreate(opt.id)}
                >
                  <div style={{ fontFamily: 'Cinzel, serif', fontWeight: 'bold', fontSize: '0.95rem', color: opt.id === 'hard' ? '#e66' : opt.id === 'easy' ? '#6e6' : '#fff' }}>
                    {opt.label}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.65)', marginTop: '0.2rem' }}>{opt.desc}</div>
                  {opt.note && <div style={{ fontSize: '0.7rem', color: 'rgba(201,168,76,0.7)', marginTop: '0.25rem' }}>{opt.note}</div>}
                </button>
              ))}
            </div>
            <button className="btn" style={{ width: '100%', marginTop: '1rem', fontSize: '0.8rem' }} onClick={() => setPendingNewName(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
