import React, { useState, useEffect } from 'react'
import SummonPage from './pages/SummonPage'
import HeroesPage from './pages/HeroesPage'
import TowerPage from './pages/TowerPage'
import BasePage from './pages/BasePage'
import LogPage from './pages/LogPage'
import InventoryPage from './pages/InventoryPage'
import ProfileSelect from './components/ProfileSelect'
import HeroChat from './components/HeroChat'
import ToastContainer from './components/ToastContainer'
import { getBase, listProfiles, grantResources, clearDevInventory, setDevLevel, grantInventoryItem, listHeroes } from './api/client'
import { initAudio, setSoundEnabled, isSoundEnabled, playClick, setBgmVolume, setSfxVolume } from './audio'

const TABS = [
  { id: 'summon', label: 'Summon' },
  { id: 'heroes', label: 'Heroes' },
  { id: 'inventory', label: 'Items' },
  { id: 'tower',  label: 'Tower' },
  { id: 'base',   label: 'Base' },
]

export default function App() {
  const [activeProfile, setActiveProfile] = useState(null)
  const [tab, setTab] = useState('summon')
  const [gold, setGold] = useState(null)
  const [supplies, setSupplies] = useState(null)
  const [gems, setGems] = useState(null)
  const [showSettings, setShowSettings] = useState(false)
  const [soundOn, setSoundOn] = useState(true)
  const [bgmVol, setBgmVol] = useState(50)
  const [sfxVol, setSfxVol] = useState(50)
  const [devHeroes, setDevHeroes] = useState([])
  const [devHeroId, setDevHeroId] = useState('')
  const [devLevel, setDevLevel_] = useState(10)
  const [devItemName, setDevItemName] = useState('')
  const [devItemType, setDevItemType] = useState('material')
  const [devItemQty, setDevItemQty] = useState(5)
  const [devBusy, setDevBusy] = useState(false)

  useEffect(() => { 
    checkProfile()
    
    // Global click listener for buttons to play sound
    const handleGlobalClick = (e) => {
      if (e.target.closest('button')) {
        playClick()
      }
    }
    document.addEventListener('click', handleGlobalClick)
    return () => document.removeEventListener('click', handleGlobalClick)
  }, [])

  async function checkProfile() {
    try {
      const data = await listProfiles()
    } catch {}
  }

  async function refreshResources() {
    if (!activeProfile) return
    try {
      const data = await getBase()
      setGold(data.gold)
      setSupplies(data.supplies)
      setGems(data.gems || 0)
    } catch {}
  }

  useEffect(() => {
    if (activeProfile) refreshResources()
    if (activeProfile && activeProfile.toLowerCase().startsWith('test')) {
      listHeroes(true).then(setDevHeroes).catch(() => {})
    }
  }, [activeProfile])

  async function handleDevClearInventory() {
    if (!confirm('Wipe all equipment, materials, potions, and scrolls on this profile?')) return
    setDevBusy(true)
    try {
      await clearDevInventory()
      alert('Inventory cleared.')
    } catch (e) { alert(e.message) } finally { setDevBusy(false) }
  }

  async function handleDevSetLevel() {
    if (!devHeroId) return
    setDevBusy(true)
    try {
      const res = await setDevLevel(Number(devHeroId), Number(devLevel))
      alert(`Set to level ${res.level}${res.capped ? ' (capped by star)' : ''}.`)
    } catch (e) { alert(e.message) } finally { setDevBusy(false) }
  }

  async function handleDevGrantItem() {
    if (!devItemName.trim()) return
    setDevBusy(true)
    try {
      await grantInventoryItem(devItemName.trim(), devItemType, Number(devItemQty))
      alert(`Granted ${devItemQty}x ${devItemName}.`)
    } catch (e) { alert(e.message) } finally { setDevBusy(false) }
  }

  async function handleGrantResources(gold, gems, supplies) {
    try {
      await grantResources(gold, gems, supplies)
      refreshResources()
    } catch (e) {
      alert(e.message)
    }
  }

  function toggleSound() {
    initAudio()
    const next = !soundOn
    setSoundOn(next)
    setSoundEnabled(next)
  }

  if (!activeProfile) {
    return <ProfileSelect onSelect={(p) => {
      initAudio()
      setActiveProfile(p)
    }} />
  }

  const pages = {
    summon: <SummonPage onGoldChange={refreshResources} />,
    heroes: <HeroesPage />,
    inventory: <InventoryPage />,
    tower:  <TowerPage onGoldChange={refreshResources} />,
    base:   <BasePage onGoldChange={refreshResources} />,
    log:    <LogPage />,
  }

  return (
    <div className="app">
      <header className="app-header" style={{ display: 'flex', justifyContent: 'space-between', width: '100%', padding: '1rem 2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <h1 style={{ fontSize: '2.5rem', margin: 0 }}>⬡ Tower Gacha</h1>
          <div className="text-dim" style={{ borderLeft: '2px solid var(--border)', paddingLeft: '2rem', fontSize: '1.6rem' }}>
            Profile: <span className="text-gold" style={{ fontSize: '2.2rem', fontWeight: 'bold' }}>{activeProfile}</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '3rem' }}>
          <button className="btn" style={{ padding: '0.8rem 1.5rem', fontSize: '1.2rem' }} onClick={() => setShowSettings(true)}>
            ⚙️ Settings
          </button>
          {gold !== null && (
            <div className="gold-display" style={{ display: 'flex', gap: '2rem', fontSize: '1.4rem' }}>
              <span style={{ color: 'var(--gold)', fontWeight: 'bold' }}>🪙 {gold.toLocaleString()} GOLD</span>
              {gems !== null && <span style={{ color: '#00ffff', fontWeight: 'bold', textShadow: '0 0 5px rgba(0,255,255,0.5)' }}>💎 {gems.toLocaleString()} GEMS</span>}
              {supplies !== null && <span style={{ color: 'var(--subtext)', fontWeight: 'bold' }}>📦 {supplies.toLocaleString()} SUPPLIES</span>}
            </div>
          )}
        </div>
      </header>

      <nav className="tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`tab-btn ${tab === t.id ? 'active' : ''}`}
            onClick={() => { setTab(t.id); if (t.id === 'base' || t.id === 'summon' || t.id === 'tower') refreshResources() }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="main-content">
        {pages[tab]}
      </main>

      {activeProfile && activeProfile.toLowerCase().startsWith('test') && (
        <div style={{
          position: 'fixed', top: '50%', right: 0, transform: 'translateY(-50%)',
          zIndex: 500, background: 'rgba(20,10,10,0.92)', border: '1px solid rgba(255,100,100,0.4)',
          borderRight: 'none', borderRadius: '8px 0 0 8px', padding: '1rem',
          display: 'flex', flexDirection: 'column', gap: '0.5rem', width: '230px',
          maxHeight: '90vh', overflowY: 'auto',
          boxShadow: '-4px 0 12px rgba(0,0,0,0.4)'
        }}>
          <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1rem', color: '#ff8080' }}>🛠 Dev Tools</div>
          <div className="text-dim" style={{ fontSize: '0.7rem', marginBottom: '0.3rem' }}>
            Profile "{activeProfile}" only
          </div>
          <button className="btn" style={{ fontSize: '0.85rem' }} onClick={() => handleGrantResources(10000, 0, 0)}>+10,000 Gold</button>
          <button className="btn" style={{ fontSize: '0.85rem' }} onClick={() => handleGrantResources(0, 500, 0)}>+500 Gems</button>
          <button className="btn" style={{ fontSize: '0.85rem' }} onClick={() => handleGrantResources(0, 0, 500)}>+500 Supplies</button>

          <div style={{ borderTop: '1px solid rgba(255,100,100,0.25)', marginTop: '0.4rem', paddingTop: '0.5rem' }}>
            <button className="btn" style={{ fontSize: '0.8rem', width: '100%', color: '#ff8080' }} disabled={devBusy} onClick={handleDevClearInventory}>
              ⚠ Clear Inventory
            </button>
          </div>

          <div style={{ borderTop: '1px solid rgba(255,100,100,0.25)', marginTop: '0.4rem', paddingTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            <div className="text-dim" style={{ fontSize: '0.7rem' }}>Set Hero Level</div>
            <select className="input" style={{ fontSize: '0.75rem', padding: '0.3rem' }} value={devHeroId} onChange={e => setDevHeroId(e.target.value)}>
              <option value="">Select hero...</option>
              {devHeroes.map(h => <option key={h.id} value={h.id}>{h.name} (Lv.{h.level})</option>)}
            </select>
            <div style={{ display: 'flex', gap: '0.3rem' }}>
              <input type="number" className="input" style={{ fontSize: '0.75rem', padding: '0.3rem', flex: 1 }} value={devLevel} onChange={e => setDevLevel_(e.target.value)} />
              <button className="btn" style={{ fontSize: '0.75rem' }} disabled={devBusy || !devHeroId} onClick={handleDevSetLevel}>Set</button>
            </div>
          </div>

          <div style={{ borderTop: '1px solid rgba(255,100,100,0.25)', marginTop: '0.4rem', paddingTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            <div className="text-dim" style={{ fontSize: '0.7rem' }}>Grant Item</div>
            <input type="text" className="input" placeholder="Item name" style={{ fontSize: '0.75rem', padding: '0.3rem' }} value={devItemName} onChange={e => setDevItemName(e.target.value)} />
            <div style={{ display: 'flex', gap: '0.3rem' }}>
              <select className="input" style={{ fontSize: '0.75rem', padding: '0.3rem', flex: 1 }} value={devItemType} onChange={e => setDevItemType(e.target.value)}>
                <option value="material">Material</option>
                <option value="potion">Potion</option>
                <option value="scroll">Scroll</option>
              </select>
              <input type="number" className="input" style={{ fontSize: '0.75rem', padding: '0.3rem', width: '50px' }} value={devItemQty} onChange={e => setDevItemQty(e.target.value)} />
            </div>
            <button className="btn" style={{ fontSize: '0.75rem' }} disabled={devBusy || !devItemName.trim()} onClick={handleDevGrantItem}>Grant</button>
          </div>
        </div>
      )}



      {showSettings && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.85)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(5px)'
        }} onClick={() => setShowSettings(false)}>
          <div className="card" style={{ width: '300px', textAlign: 'center' }} onClick={e => e.stopPropagation()}>
            <h2 style={{ fontFamily: 'Cinzel, serif', color: 'var(--gold)', marginBottom: '1.5rem' }}>Settings</h2>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <button className="btn" onClick={toggleSound}>
                {soundOn ? '🔊 Sound Master: ON' : '🔇 Sound Master: OFF'}
              </button>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'flex-start' }}>
                <label className="text-dim text-sm">Music Volume</label>
                <input type="range" min="0" max="100" value={bgmVol} onChange={(e) => {
                  const val = parseInt(e.target.value)
                  setBgmVol(val)
                  setBgmVolume(val / 100)
                }} style={{ width: '100%' }} />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'flex-start' }}>
                <label className="text-dim text-sm">SFX Volume</label>
                <input type="range" min="0" max="100" value={sfxVol} onChange={(e) => {
                  const val = parseInt(e.target.value)
                  setSfxVol(val)
                  setSfxVolume(val / 100)
                }} style={{ width: '100%' }} />
              </div>
              
              <button className="btn" onClick={() => {
                setShowSettings(false)
                setActiveProfile(null)
              }}>
                🔄 Switch Profile (Main Menu)
              </button>
              
              <button className="btn" style={{ marginTop: '1rem', background: 'var(--border)' }} onClick={() => setShowSettings(false)}>
                Close
              </button>
            </div>
            
            <div className="text-dim" style={{ fontSize: '0.65rem', marginTop: '1.5rem' }}>
              Tower Gacha Pre-Alpha
            </div>
          </div>
        </div>
      )}
      <ToastContainer />
    </div>
  )
}
