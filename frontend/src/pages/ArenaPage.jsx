import React, { useState, useEffect } from 'react'
import { getAllTeams, getArenaSnapshot } from '../api/client'
import {
  getArenaServerUrl, setArenaServerUrl, getArenaToken, getArenaUsername, clearArenaSession,
  arenaRegister, arenaLogin, arenaSubmitTeam, arenaChallenge, arenaLeaderboard,
} from '../api/arenaServerClient'

export default function ArenaPage() {
  const [serverUrl, setServerUrl] = useState(getArenaServerUrl())
  const [token, setToken] = useState(getArenaToken())
  const [username, setUsername] = useState(getArenaUsername())

  const [authUsername, setAuthUsername] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authMode, setAuthMode] = useState('login') // 'login' | 'register'
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  const [teams, setTeams] = useState({})
  const [teamId, setTeamId] = useState(1)
  const [teamSubmitted, setTeamSubmitted] = useState(false)

  const [opponent, setOpponent] = useState('')
  const [fightResult, setFightResult] = useState(null)

  const [leaderboard, setLeaderboard] = useState([])

  useEffect(() => {
    getAllTeams().then(setTeams).catch(() => {})
  }, [])

  useEffect(() => {
    if (serverUrl) refreshLeaderboard()
  }, [serverUrl])

  function refreshLeaderboard() {
    arenaLeaderboard().then(data => setLeaderboard(data.leaderboard)).catch(() => {})
  }

  function handleSaveUrl() {
    setArenaServerUrl(serverUrl)
    setMsg('Arena server address saved.')
    refreshLeaderboard()
  }

  async function handleAuth(e) {
    e.preventDefault()
    if (!serverUrl) { setMsg('Set the Arena server address first.'); return }
    setBusy(true)
    setMsg(null)
    try {
      if (authMode === 'register') {
        await arenaRegister(authUsername.trim(), authPassword)
        setMsg('Registered. Now log in.')
        setAuthMode('login')
      } else {
        await arenaLogin(authUsername.trim(), authPassword)
        setToken(getArenaToken())
        setUsername(getArenaUsername())
        setMsg(`Logged in as ${getArenaUsername()}.`)
        refreshLeaderboard()
      }
    } catch (err) {
      setMsg(err.message)
    } finally {
      setBusy(false)
    }
  }

  function handleLogout() {
    clearArenaSession()
    setToken('')
    setUsername('')
  }

  async function handleSubmitTeam() {
    setBusy(true)
    setMsg(null)
    setTeamSubmitted(false)
    try {
      const snapshot = await getArenaSnapshot(teamId)
      await arenaSubmitTeam(snapshot.team)
      setTeamSubmitted(true)
      setMsg(`Submitted Team ${teamId} (${snapshot.team.length} heroes) to the Arena.`)
    } catch (err) {
      setMsg(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleChallenge(e) {
    e.preventDefault()
    setBusy(true)
    setMsg(null)
    setFightResult(null)
    try {
      const result = await arenaChallenge(opponent.trim())
      setFightResult(result)
      refreshLeaderboard()
    } catch (err) {
      setMsg(err.message)
    } finally {
      setBusy(false)
    }
  }

  const teamEntries = Object.entries(teams).filter(([, heroes]) => heroes.length > 0)

  return (
    <div className="page">
      <div className="section-header">Arena</div>
      <div className="text-dim text-sm" style={{ marginBottom: '1rem' }}>
        PvP combat against other players' submitted teams. Heroes never die here and nothing
        here ever touches your save — your local stats are snapshotted once when you submit a team.
      </div>

      <div className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
        <div className="text-dim text-sm" style={{ marginBottom: '0.5rem' }}>Arena Server</div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            className="input"
            placeholder="http://your-server-address:8001"
            value={serverUrl}
            onChange={e => setServerUrl(e.target.value)}
            style={{ flex: 1, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', padding: '0.5rem', color: '#fff', borderRadius: 4 }}
          />
          <button className="btn" onClick={handleSaveUrl}>Save</button>
        </div>
      </div>

      {msg && <div className="text-sm" style={{ marginBottom: '1rem', color: 'var(--gold)' }}>{msg}</div>}

      {!token ? (
        <div className="card" style={{ padding: '1rem', maxWidth: 400 }}>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
            <button className={`btn ${authMode === 'login' ? 'btn-gold' : ''}`} onClick={() => setAuthMode('login')}>Login</button>
            <button className={`btn ${authMode === 'register' ? 'btn-gold' : ''}`} onClick={() => setAuthMode('register')}>Register</button>
          </div>
          <form onSubmit={handleAuth} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <input type="text" className="input" placeholder="Username" value={authUsername} onChange={e => setAuthUsername(e.target.value)}
              style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', padding: '0.5rem', color: '#fff', borderRadius: 4 }} />
            <input type="password" className="input" placeholder="Password" value={authPassword} onChange={e => setAuthPassword(e.target.value)}
              style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', padding: '0.5rem', color: '#fff', borderRadius: 4 }} />
            <button type="submit" className="btn btn-gold" disabled={busy || !authUsername.trim() || !authPassword}>
              {authMode === 'login' ? 'Log In' : 'Register'}
            </button>
          </form>
        </div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: '1rem', padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>Logged in as <span className="text-gold" style={{ fontWeight: 'bold' }}>{username}</span></div>
            <button className="btn" onClick={handleLogout}>Log Out</button>
          </div>

          <div className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
            <div className="text-dim text-sm" style={{ marginBottom: '0.5rem' }}>Submit a Team to the Arena</div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <select className="input" value={teamId} onChange={e => setTeamId(Number(e.target.value))}
                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', padding: '0.5rem', color: '#fff', borderRadius: 4 }}>
                {teamEntries.length === 0 && <option value={1}>Team 1 (empty)</option>}
                {teamEntries.map(([id, heroes]) => (
                  <option key={id} value={id}>Team {id} — {heroes.map(h => h.name).join(', ')}</option>
                ))}
              </select>
              <button className="btn btn-gold" disabled={busy} onClick={handleSubmitTeam}>Submit Team</button>
              {teamSubmitted && <span style={{ color: 'var(--green)' }}>✓ Submitted</span>}
            </div>
          </div>

          <div className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
            <div className="text-dim text-sm" style={{ marginBottom: '0.5rem' }}>Challenge a Player</div>
            <form onSubmit={handleChallenge} style={{ display: 'flex', gap: '0.5rem' }}>
              <input type="text" className="input" placeholder="Opponent's username" value={opponent} onChange={e => setOpponent(e.target.value)}
                style={{ flex: 1, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', padding: '0.5rem', color: '#fff', borderRadius: 4 }} />
              <button type="submit" className="btn btn-gold" disabled={busy || !opponent.trim()}>Fight</button>
            </form>
          </div>

          {fightResult && (
            <div className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
              <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.2rem', marginBottom: '0.5rem', color: fightResult.winner === username ? 'var(--green)' : 'var(--red)' }}>
                {fightResult.winner === username ? '✓ Victory' : '✗ Defeat'} — {fightResult.winner} defeated {fightResult.loser}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', maxHeight: '40vh', overflowY: 'auto' }}>
                {fightResult.log.map((line, i) => (
                  <div key={i} className="text-dim text-sm">{line}</div>
                ))}
              </div>
            </div>
          )}

          <div className="card" style={{ padding: '1rem' }}>
            <div className="text-dim text-sm" style={{ marginBottom: '0.5rem' }}>Leaderboard</div>
            {leaderboard.length === 0 && <div className="text-dim text-sm">No matches recorded yet.</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              {leaderboard.map((p, i) => (
                <div key={p.username} style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem' }}>
                  <span className="text-dim" style={{ minWidth: 30 }}>#{i + 1}</span>
                  <span style={{ color: p.username === username ? 'var(--gold)' : 'inherit', flex: 1 }}>{p.username}</span>
                  <span className="text-dim">{p.wins}W / {p.losses}L</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
