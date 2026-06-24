import React, { useState, useEffect } from 'react'
import { getBase, getFacilities, buildFacility, upgradeFacility, assignFacility, removeFacility, restHeroes, listHeroes, configTraining, getMageTowerUpgrades, buyResearchUpgrade, craftMaterialEquipment, craftBandages, getBaseFloors, assignBaseFloor, getLegacies, getChatLogs, renameBase, upgradeBase, getMarketCatalog, purchaseMarketItem } from '../api/client'

const FACILITY_TOOLTIPS = {
  "Forge": "Crafts powerful weapons, armor, and accessories. Quality is capped by your single best Blacksmith — more Blacksmiths of that same tier assigned together adds a smaller bonus on top.",
  "Infirmary": "Heals trauma passively over time and crafts Bandages (auto-used to patch up your most injured heroes before the next floor). Assign Medics and Priests for better results.",
  "Vault": "Expands equipment storage capacity. Quartermasters manage the Vault effectively.",
  "Restaurant": "Cooks advanced meals to increase morale. Assign Chefs to maximize food quality.",
  "Alchemist Lab": "Brews potions and elixirs. Alchemists and Mages excel in this facility.",
  "Workshop": "Builds base upgrades and gadgets. Magic Engineers are the best fit.",
  "The Market": "Generates passive gold over time and stocks a small shop for supplies, materials, and bandages. Merchants and Quartermasters excel here.",
  "The Farm": "Generates passive supplies over time. Merchants and Druids excel here.",
  "Training Grounds": "Allows heroes to spar for EXP. Warriors, Spearmen, and Tacticians thrive here.",
  "Mage Tower": "Conducts magical research. Magic Engineers are the most effective, with Mages and Spellswords close behind."
}

export default function BasePage({ onGoldChange, onSubTabChange, tourTargetSubTab }) {
  const [activeTab, setActiveTab] = useState('lobby')
  const [base, setBase] = useState(null)
  const [facilitiesData, setFacilitiesData] = useState(null)
  const [baseHeroes, setBaseHeroes] = useState([])
  const [resting, setResting] = useState(false)
  const [msg, setMsg] = useState(null)
  const [facilityLoading, setFacilityLoading] = useState(false)
  const [mageUpgrades, setMageUpgrades] = useState(null)
  const [crafting, setCrafting] = useState(false)
  const [marketCatalog, setMarketCatalog] = useState({})
  const [purchasing, setPurchasing] = useState(false)
  
  // Legacy & Floors
  const [legacies, setLegacies] = useState([])
  const [expandedLegacyId, setExpandedLegacyId] = useState(null)
  const [legacyPage, setLegacyPage] = useState(0)
  const LEGACIES_PER_PAGE = 10
  const [floorsData, setFloorsData] = useState(null)
  const [assigning, setAssigning] = useState(false)
  const [chats, setChats] = useState([])
  const [newChatIds, setNewChatIds] = useState(new Set())
  const seenChatIds = React.useRef(new Set())
  const hasLoadedChatsOnce = React.useRef(false)

  function applyChats(ch) {
    const list = ch || []
    const fresh = hasLoadedChatsOnce.current ? list.filter(c => !seenChatIds.current.has(c.id)).map(c => c.id) : []
    list.forEach(c => seenChatIds.current.add(c.id))
    hasLoadedChatsOnce.current = true
    setChats(list)
    if (fresh.length) {
      setNewChatIds(new Set(fresh))
      setTimeout(() => setNewChatIds(new Set()), 3000)
    }
  }
  
  const [sortMode, setSortMode] = useState('level-desc')
  const [filterClass, setFilterClass] = useState('All')
  
  useEffect(() => { loadAll() }, [])

  useEffect(() => { onSubTabChange?.(activeTab) }, [activeTab])

  // Hero Chatter feed polls on its own, faster cadence than the rest of the
  // page — it should feel like an ongoing conversation, not a static log
  // that only updates on a full page reload.
  useEffect(() => {
    const interval = setInterval(() => {
      getChatLogs(5).then(applyChats).catch(() => {})
    }, 20000)
    return () => clearInterval(interval)
  }, [])

  async function loadAll() {
    try {
      const [b, fac, heroes, leg, flrs, ch, catalog] = await Promise.all([
        getBase(),
        getFacilities(),
        listHeroes(true),
        getLegacies().catch(() => ({ legacies: [] })),
        getBaseFloors().catch(() => ({ floors: [], base_heroes: [] })),
        getChatLogs(5).catch(() => []),
        getMarketCatalog().catch(() => ({}))
      ])
      setBase(b)
      setFacilitiesData(fac)
      setBaseHeroes(heroes.filter(h => h.is_alive === 1 && h.is_on_team === 0))
      setLegacies(leg.legacies || [])
      setFloorsData(flrs)
      applyChats(ch)
      setMarketCatalog(catalog)
      
      const hasMage = fac.built?.some(f => f.type === 'Mage Tower')
      if (hasMage) {
        const mage = await getMageTowerUpgrades().catch(() => null)
        setMageUpgrades(mage)
      }
    } catch (e) {
      console.error(e)
    }
  }

const handleRenameBase = async () => {
    const newName = prompt("Enter a new name for your base:", base.name);
    if (!newName) return;
    try {
      await renameBase(newName);
      loadAll();
    } catch(e) {
      alert(e.message || "Failed to rename base.");
    }
  };

  const handleRest = async () => {
    setResting(true)
    try {
      const data = await restHeroes()
      alert(`Rested ${data.rested} heroes — Health fully restored, morale/stress/trauma recovered. Cost: ${data.cost} supplies.`)
      loadAll()
    } catch (e) {
      alert(e.message || "Cannot rest.")
    } finally {
      setResting(false)
    }
  }

  const handleUpgradeBase = async () => {
    try {
      await upgradeBase()
      alert("Base Upgraded! Max Roster Size increased.")
      loadAll()
      if (onGoldChange) onGoldChange()
    } catch(e) { alert(e.message || "Failed to upgrade") }
  }



  async function handleBuildFacility(type) {
    setFacilityLoading(true)
    try {
      await buildFacility(type)
      loadAll()
      if (onGoldChange) onGoldChange()
    } catch (e) {
      alert(e.message)
    } finally {
      setFacilityLoading(false)
    }
  }

  async function handleUpgradeFacility(facId) {
    setFacilityLoading(true)
    try {
      await upgradeFacility(facId)
      loadAll()
      if (onGoldChange) onGoldChange()
    } catch (e) {
      alert(e.message)
    } finally {
      setFacilityLoading(false)
    }
  }

  async function handleAssignFacility(facId, heroId) {
    setFacilityLoading(true)
    try {
      await assignFacility(facId, heroId)
      loadAll()
    } catch (e) {
      alert(e.message)
    } finally {
      setFacilityLoading(false)
    }
  }

  async function handleRemoveFacility(heroId) {
    setFacilityLoading(true)
    try {
      await removeFacility(heroId)
      loadAll()
    } catch (e) {
      alert(e.message)
    } finally {
      setFacilityLoading(false)
    }
  }

  async function handleBuyResearch(upgradeId) {
    setFacilityLoading(true)
    try {
      await buyResearchUpgrade(upgradeId)
      loadAll()
    } catch (e) {
      alert(e.message)
    } finally {
      setFacilityLoading(false)
    }
  }

  async function handleCraft(heroId, slot) {
    setCrafting(true)
    try {
      await craftMaterialEquipment(heroId, slot)
      loadAll()
      if (onGoldChange) onGoldChange()
      alert("Crafted successfully!")
    } catch (e) {
      alert(e.message)
    } finally {
      setCrafting(false)
    }
  }

  async function handleCraftBandages(heroId) {
    setCrafting(true)
    try {
      const res = await craftBandages(heroId, 1)
      loadAll()
      if (onGoldChange) onGoldChange()
      alert(`Crafted a Bandage (${res.total} in stock). Auto-used on your most injured heroes before your next floor.`)
    } catch (e) {
      alert(e.message)
    } finally {
      setCrafting(false)
    }
  }

  async function handlePurchase(itemId) {
    setPurchasing(true)
    try {
      const res = await purchaseMarketItem(itemId)
      loadAll()
      if (onGoldChange) onGoldChange()
      const detail = res.material ? `${res.amount}x ${res.material}` : res.supplies ? `${res.supplies} supplies` : ''
      alert(`Purchased ${res.item}! +${detail}`)
    } catch (e) {
      alert(e.message)
    } finally {
      setPurchasing(false)
    }
  }

  async function handleAssignFloor(heroId, floorNum) {
    setAssigning(true)
    try {
      await assignBaseFloor(heroId, floorNum === null ? 0 : floorNum)
      loadAll()
    } catch(e) {
      alert(e.message || e)
    } finally {
      setAssigning(false)
    }
  }

  if (!base) return <div className="page text-dim">Loading...</div>
  if (!facilitiesData) return <div className="page text-dim">Loading facilities...</div>

  let materials = {}
  try { materials = JSON.parse(base.materials || '{}') } catch {}

  
  let goldGen = 0;
  let suppliesGen = 0;
  if (facilitiesData && facilitiesData.built) {
    facilitiesData.built.forEach(f => {
      let base_amt = f.type === 'The Market' ? 100 * f.level : 5 * f.level;
      let multiplier = 1.0 + ((f.heroes?.length || 0) * 0.10);
      if (f.type === 'The Market') goldGen += Math.floor(base_amt * multiplier);
      if (f.type === 'The Farm') suppliesGen += Math.floor(base_amt * multiplier);
    });
  }

  const renderTabs = () => (
    <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', overflowX: 'auto' }}>
      {['lobby', 'facilities', 'legacy', 'floors'].map(tab => {
        const locked = !!tourTargetSubTab && tab !== tourTargetSubTab
        return (
          <button key={tab} className={`tab-btn ${activeTab === tab ? 'active' : ''}`} disabled={locked} onClick={() => { if (!locked) setActiveTab(tab) }}
          style={{
            background: 'none', border: 'none', padding: '0.5rem 1rem', cursor: locked ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap',
            color: activeTab === tab ? 'var(--gold)' : 'var(--text-dim)',
            borderBottom: activeTab === tab ? '2px solid var(--gold)' : '2px solid transparent',
            fontFamily: 'Cinzel, serif', fontSize: '1.1rem', textTransform: 'uppercase',
            opacity: locked ? 0.35 : 1,
            boxShadow: tab === tourTargetSubTab ? '0 0 8px var(--gold)' : 'none',
          }}>
            {tab === 'floors' ? 'Base Hierarchy' : tab === 'legacy' ? 'Legacies' : tab === 'lobby' ? 'The Lobby' : tab}
          </button>
        )
      })}
    </div>
  )


const getGenRate = (fac) => {
    if (fac.type !== 'The Market' && fac.type !== 'The Farm') return null;
    let base_amt = fac.type === 'The Market' ? 100 * fac.level : 5 * fac.level;
    let multiplier = 1.0 + ((fac.heroes || []).length * 0.10);
    let amt = Math.floor(base_amt * multiplier);
    let resName = fac.type === 'The Market' ? 'Gold' : 'Supplies';
    return `Generating: +${amt} ${resName} / 5 mins`;
  };

  return (
    <div className="page">
      <div className="section-header">Home Base</div>

      {renderTabs()}

      {activeTab === 'lobby' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Top Row: Base Stats & Recovery */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1.5rem' }}>
            
            {/* The Lobby Profile */}
            <div className="card" style={{ padding: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
                <div style={{ fontFamily: 'Cinzel, serif', fontSize: '2.0rem', color: 'var(--gold)' }}>
                  {base.name} <span style={{ fontSize: '1.4rem', color: 'var(--text-dim)' }}>(Lv.{base.level})</span>
                </div>
                <button className="btn" style={{ padding: '0.4rem', fontSize: '0.9rem' }} onClick={handleRenameBase} title="Rename Base">✎ Edit</button>
              </div>
              
              <div style={{ display: 'flex', gap: '2rem', marginBottom: '1.5rem', marginTop: '1rem' }}>
                <div>
                  <div className="text-dim" style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Total Treasury</div>
                  <div className="text-gold" style={{ fontFamily: 'Cinzel, serif', fontSize: '1.5rem' }}>{base.gold.toLocaleString()} Gold</div>
                </div>
                <div>
                  <div className="text-dim" style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Total Supplies</div>
                  <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.5rem', color: '#c7e0f4' }}>{base.supplies?.toLocaleString()} Supplies</div>
                </div>
              </div>
              
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
                <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.2rem', color: 'var(--text-hi)', marginBottom: '1rem' }}>Resource Generation</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '1.1rem' }}>
                  <span className="text-dim">The Market:</span>
                  <span className="text-gold">+{goldGen} Gold / 5 mins</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1.1rem' }}>
                  <span className="text-dim">The Farm:</span>
                  <span style={{ color: '#c7e0f4' }}>+{suppliesGen} Supplies / 5 mins</span>
                </div>
              </div>
            </div>

            {/* Base Expansion */}
            <div className="card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}>
              <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.8rem', color: 'var(--text-hi)', marginBottom: '1rem' }}>Base Expansion</div>
              <div className="text-dim" style={{ fontSize: '1.1rem', lineHeight: 1.6, marginBottom: 'auto' }}>
                Upgrading the base expands your facilities and allows you to recruit more heroes to your cause.<br/><br/>
                Current Max Roster: <span className="text-hi" style={{ fontSize: '1.3rem' }}>{base.max_roster_size || 10}</span><br/>
                Next Upgrade: <span className="text-green">+10 Roster Slots</span>
              </div>
              <button className="btn btn-gold" onClick={handleUpgradeBase} style={{ width: '100%', padding: '1rem', fontSize: '1.1rem', marginTop: '2rem' }}>
                Upgrade Base ({5000 * base.level}G)
              </button>
            </div>

            {/* Rest & Recovery */}
            <div className="card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}>
              <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.8rem', color: 'var(--text-hi)', marginBottom: '1rem' }}>Rest & Recovery</div>
              <div className="text-dim" style={{ fontSize: '1.1rem', lineHeight: 1.6, marginBottom: 'auto' }}>
                Resting at base recovers morale (+25), reduces stress (-20), and slowly heals trauma (-5) for all living heroes.<br/><br/>
                Resting costs 50 supplies and has a 5-minute cooldown.
              </div>
              {(() => {
                const now = Date.now() / 1000;
                const lastRest = base.last_rest_time || 0;
                const cd = 300;
                const rem = Math.max(0, cd - (now - lastRest));
                const isCooldown = rem > 0;
                return (
                  <button className="btn btn-gold" onClick={handleRest} disabled={resting || isCooldown} style={{ width: '100%', padding: '1rem', fontSize: '1.1rem', marginTop: '2rem' }}>
                    {resting ? 'Resting...' : isCooldown ? `Cooldown (${Math.ceil(rem)}s)` : 'Rest All Heroes (Costs 50 Supplies)'}
                  </button>
                )
              })()}
              {msg && <div className="text-green" style={{ marginTop: '1rem', fontSize: '1.1rem', textAlign: 'center' }}>{msg}</div>}
            </div>

            </div>
            
            {/* Bottom Row: Hero Chatter Box */}
          <div className="card" style={{ padding: '1.5rem', minHeight: '250px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.4rem', color: 'var(--gold)', marginBottom: '1rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              Hero Chatter
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.7rem', color: 'var(--green)', fontFamily: 'monospace', letterSpacing: '1px' }}>
                <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--green)', animation: 'pulse-live 1.5s ease-in-out infinite' }} />
                LIVE
              </span>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              {chats && chats.length > 0 ? chats.map(chat => (
                <div key={chat.id} style={{ marginBottom: '0.6rem', transition: 'background 1s ease', background: newChatIds.has(chat.id) ? 'rgba(201,168,76,0.12)' : 'transparent', borderRadius: 4, padding: newChatIds.has(chat.id) ? '0.4rem' : '0' }}>
                  <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.2rem' }}>
                    <span className="text-dim" style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>[{new Date(chat.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}]</span>
                    <span style={{ color: 'var(--gold)', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>[{chat.location}]</span>
                  </div>
                  {(chat.messages || []).map((m, i) => (
                    <div key={i} style={{ fontSize: '1.05rem', marginLeft: '0.5rem' }}>
                      <span className="text-hi" style={{ fontFamily: 'Cinzel, serif' }}>{m.speaker}:</span> {m.message}
                    </div>
                  ))}
                </div>
              )) : (
                <div className="text-dim" style={{ fontStyle: 'italic', textAlign: 'center', marginTop: '2rem' }}>The lobby is quiet...</div>
              )}
            </div>
          </div>

        </div>
      )}

      {activeTab === 'facilities' && (
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          {/* Left Column: Built Facilities */}
          <div style={{ flex: '2 1 500px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {facilitiesData.built.sort((a,b) => a.cost - b.cost).map(fac => (
              <div key={fac.id} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <h3 style={{ fontFamily: 'Cinzel, serif', color: 'var(--gold)', margin: 0 }}>{fac.type} (Lv.{fac.level})</h3>
                        <span title={FACILITY_TOOLTIPS[fac.type] || "Base facility."} style={{ fontSize: '0.8rem', color: 'var(--gold)', cursor: 'help' }}>[?]</span>
                      </div>
                      {getGenRate(fac) && (
                        <div style={{ fontSize: '0.9rem', color: 'var(--star2)', marginTop: '0.2rem', fontFamily: 'Cinzel, serif' }}>
                          {getGenRate(fac)}
                        </div>
                      )}
                    </div>
                  {fac.level < fac.max_level && (
                    <button className="btn" onClick={() => handleUpgradeFacility(fac.id)} disabled={facilityLoading || base.gold < fac.upgrade_cost} style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem' }}>
                      Upgrade ({fac.upgrade_cost}g)
                    </button>
                  )}
                </div>
                
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                  {fac.heroes.map(h => (
                    <div key={h.id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'rgba(0,0,0,0.3)', padding: '0.5rem 0.75rem', borderRadius: 6 }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                            <img src={`http://localhost:8000/${h.portrait_path}`} alt={h.name} style={{ width: 100, height: 100, borderRadius: '50%', objectFit: 'cover', objectPosition: 'center 15%', border: '1px solid var(--border)' }} />
                            <div className="text-hi" style={{ fontSize: '0.8rem', marginTop: '0.3rem', textAlign: 'center' }}>{h.name}</div>
                          </div>
                      <span style={{ fontSize: '0.95rem' }}>{h.name}</span>
                      <button onClick={() => handleRemoveFacility(h.id)} style={{ background: 'none', border: 'none', color: 'var(--red)', cursor: 'pointer', marginLeft: '0.5rem' }}>&times;</button>
                      {fac.type === 'Forge' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', marginLeft: '0.5rem' }}>
                          <button onClick={() => handleCraft(h.id, 'weapon')} disabled={crafting} className="btn btn-gold" style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}>Weapon (100g, 3 Iron, 1 Bone)</button>
                          <button onClick={() => handleCraft(h.id, 'armor')} disabled={crafting} className="btn btn-gold" style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}>Armor (100g, 2 Slime, 2 Iron)</button>
                          <button onClick={() => handleCraft(h.id, 'accessory')} disabled={crafting} className="btn btn-gold" style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}>Accessory (100g, 3 Dust, 1 Ear)</button>
                        </div>
                      )}
                      {fac.type === 'Infirmary' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', marginLeft: '0.5rem' }}>
                          <button onClick={() => handleCraftBandages(h.id)} disabled={crafting} className="btn btn-gold" style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}>Bandage (15 supplies)</button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {fac.heroes.length < fac.slots_unlocked && (
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <select id={`assign-${fac.id}`} className="input" style={{ flex: 1 }}>
                      <option value="">Assign hero...</option>
                      {baseHeroes.filter(h => !fac.heroes.find(fh => fh.id === h.id)).map(h => (
                        <option key={h.id} value={h.id}>{h.name} ({h.class_name})</option>
                      ))}
                    </select>
                    <button className="btn btn-primary" onClick={() => {
                      const sel = document.getElementById(`assign-${fac.id}`)
                      if (sel && sel.value) handleAssignFacility(fac.id, parseInt(sel.value))
                    }} disabled={facilityLoading}>Assign</button>
                  </div>
                )}

                {/* Market Shop */}
                {fac.type === 'The Market' && Object.keys(marketCatalog).length > 0 && (
                  <div style={{ marginTop: '1rem', background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: 6 }}>
                    <div className="text-dim" style={{ marginBottom: '0.5rem', fontSize: '0.85rem' }}>Shop</div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '0.5rem' }}>
                      {Object.entries(marketCatalog).map(([itemId, item]) => (
                        <div key={itemId} className="card" style={{ padding: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                          <div style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>{item.name}</div>
                          <button
                            className="btn btn-gold"
                            onClick={() => handlePurchase(itemId)}
                            disabled={purchasing || (item.currency === 'gold' ? base.gold : base.gems) < item.cost}
                            style={{ fontSize: '0.75rem', padding: '0.3rem' }}
                          >
                            {item.cost} {item.currency === 'gold' ? 'Gold 💰' : 'Gems 💎'}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Mage Tower Research */}
                {fac.type === 'Mage Tower' && mageUpgrades && (
                  <div style={{ marginTop: '1rem', background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: 6 }}>
                    <div style={{ color: 'var(--purple)', marginBottom: '0.5rem' }}>Research Points: {mageUpgrades.points}</div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '0.5rem' }}>
                      {mageUpgrades.upgrades.map(u => (
                        <div key={u.id} className="card" style={{ padding: '0.5rem' }}>
                          <div style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>{u.name} (Lv.{u.level}/{u.max_level})</div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', margin: '0.2rem 0 0.5rem' }}>{u.desc}</div>
                          <button className="btn" onClick={() => handleBuyResearch(u.id)} disabled={facilityLoading || u.level >= u.max_level || mageUpgrades.points < u.cost} style={{ width: '100%', fontSize: '0.75rem', padding: '0.2rem' }}>
                            {u.level >= u.max_level ? 'MAX' : `Research (${u.cost} RP)`}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Right Column: Available Facilities */}
          <div style={{ flex: '1 1 300px' }}>
            <h3 style={{ fontFamily: 'Cinzel, serif', color: 'var(--gold)', marginBottom: '1rem' }}>Available Facilities</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {facilitiesData.available.sort((a,b) => a.cost - b.cost).map(fac => (
                <div key={fac.type} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontFamily: 'Cinzel, serif', fontSize: '1.1rem' }}>{fac.type}</span>
                      <span title={FACILITY_TOOLTIPS[fac.type] || "Base facility."} style={{ fontSize: '0.8rem', color: 'var(--gold)', cursor: 'help' }}>[?]</span>
                    </div>
                    <button className="btn btn-gold" onClick={() => handleBuildFacility(fac.type)} disabled={facilityLoading || base.gold < fac.cost} style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}>
                      Build ({fac.cost}g)
                    </button>
                  </div>
                  {fac.floor_restricted && (
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem', fontStyle: 'italic' }}>Unlocked at Floor {fac.unlock_floor}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'legacy' && (
        <div>
          <h3 style={{ fontFamily: 'Cinzel, serif', color: 'var(--gold)', marginBottom: '1rem' }}>
            Fallen Heroes {legacies.length > 0 && <span className="text-dim text-sm">({legacies.length})</span>}
          </h3>
          {legacies.length === 0 && <div className="text-dim text-sm">No legacies found.</div>}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {legacies.slice(legacyPage * LEGACIES_PER_PAGE, (legacyPage + 1) * LEGACIES_PER_PAGE).map(leg => {
              const bonus = (() => { try { return JSON.parse(leg.bonus_json || '{}') } catch { return {} } })()
              const expanded = expandedLegacyId === leg.id
              return (
                <div key={leg.id} className="card" style={{ padding: '0.6rem 0.9rem', cursor: 'pointer' }}
                     onClick={() => setExpandedLegacyId(expanded ? null : leg.id)}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    {leg.is_sacrifice && leg.portrait_path ? (
                      <img src={`http://localhost:8000/${leg.portrait_path}`} alt={leg.hero_name} style={{ width: 32, height: 32, borderRadius: '50%', objectFit: 'cover', objectPosition: 'center 15%', border: '1px solid var(--gold)', flexShrink: 0 }} />
                    ) : (
                      <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#222', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.9rem', color: '#555', flexShrink: 0 }}>
                        ✦
                      </div>
                    )}
                    <div style={{ minWidth: 110, fontFamily: 'Cinzel, serif', color: 'var(--text-hi)', fontSize: '0.9rem' }}>{leg.hero_name}</div>
                    <div className="text-dim text-xs" style={{ minWidth: 90 }}>{leg.is_sacrifice ? 'Sacrificed' : 'Fallen'} · {leg.hero_star}★</div>
                    <div className="text-xs" style={{ color: 'var(--gold)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{leg.title}</div>
                    <div className="text-dim text-xs" style={{ flexShrink: 0 }}>{expanded ? '▲' : '▼'}</div>
                  </div>
                  {expanded && (
                    <div style={{ marginTop: '0.6rem', paddingTop: '0.6rem', borderTop: '1px solid var(--border)' }}>
                      <div className="text-xs text-dim" style={{ lineHeight: 1.4, marginBottom: '0.4rem' }}>{leg.flavor_text}</div>
                      <div className="text-xs text-dim">
                        Floors survived: {bonus.floors_survived ?? 0} · Kills: {bonus.kills ?? 0} · Legacy: {bonus.primary_bonus?.desc || 'None'}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          {legacies.length > LEGACIES_PER_PAGE && (
            <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '1rem' }}>
              <button className="btn" disabled={legacyPage === 0} onClick={() => setLegacyPage(p => Math.max(0, p - 1))}>← Prev</button>
              <div className="text-dim text-sm" style={{ alignSelf: 'center' }}>
                Page {legacyPage + 1} of {Math.ceil(legacies.length / LEGACIES_PER_PAGE)}
              </div>
              <button className="btn" disabled={(legacyPage + 1) * LEGACIES_PER_PAGE >= legacies.length} onClick={() => setLegacyPage(p => p + 1)}>Next →</button>
            </div>
          )}
        </div>
      )}

      {activeTab === 'floors' && floorsData && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.1rem', color: 'var(--text-hi)', marginBottom: '0.5rem' }}>Base Hierarchy</div>
            <div className="text-dim text-sm" style={{ lineHeight: 1.5 }}>
              Assign idle heroes to protect base floors. Drag an unassigned hero onto an empty slot on a floor to assign them. Drag an assigned hero back to unassign them.
            </div>
            <div className="text-dim text-sm" style={{ lineHeight: 1.5, marginTop: '0.5rem' }}>
              <span className="text-hi">Benefit:</span> a stationed hero gets a stat bonus (Health/STR/INT/AGI) while climbing the Tower, and recovers from fatigue faster at the base. Each floor has a fixed bonus pool that's split evenly among whoever's stationed there — higher floors have a bigger pool, but spreading more heroes across one floor shrinks everyone's individual share. Check each floor's current bonus % below before assigning.
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            {/* Unassigned Heroes with Sorting & Filtering */}
            <div className="card" style={{ flex: '1 1 300px', background: 'var(--bg-card)', padding: '1rem', borderRadius: '8px' }}
                 onDragOver={(e) => e.preventDefault()}
                 onDrop={(e) => {
                   e.preventDefault();
                   const heroId = e.dataTransfer.getData('heroId');
                   if (heroId) {
                     handleAssignFloor(heroId, null);
                   }
                 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontFamily: 'Cinzel, serif', color: 'var(--gold)', margin: 0 }}>Unassigned Heroes</h3>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                <select 
                  className="input" 
                  value={filterClass} 
                  onChange={e => setFilterClass(e.target.value)}
                  style={{ flex: 1, padding: '0.4rem', background: 'var(--bg-dark)', color: 'var(--text-hi)' }}>
                  <option value="All">All Classes</option>
                  {[...new Set(floorsData.base_heroes.map(h => h.hero_class))].map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <select 
                  className="input" 
                  value={sortMode} 
                  onChange={e => setSortMode(e.target.value)}
                  style={{ flex: 1, padding: '0.4rem', background: 'var(--bg-dark)', color: 'var(--text-hi)' }}>
                  <option value="level-desc">Level (High-Low)</option>
                  <option value="level-asc">Level (Low-High)</option>
                  <option value="star-desc">Star (High-Low)</option>
                  <option value="star-asc">Star (Low-High)</option>
                </select>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', maxHeight: '500px', overflowY: 'auto' }}>
                {(() => {
                  let heroes = [...floorsData.base_heroes]
                  if (filterClass !== 'All') {
                    heroes = heroes.filter(h => h.hero_class === filterClass)
                  }
                  heroes.sort((a, b) => {
                    if (sortMode === 'level-desc') return b.level - a.level
                    if (sortMode === 'level-asc') return a.level - b.level
                    if (sortMode === 'star-desc') return b.birth_star - a.birth_star
                    if (sortMode === 'star-asc') return a.birth_star - b.birth_star
                    return 0
                  })
                  return heroes.map(h => (
                    <div key={h.id} 
                         draggable 
                         onDragStart={(e) => e.dataTransfer.setData('heroId', h.id)}
                         style={{ cursor: 'grab' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                        <div style={{ position: 'relative' }}>
                          <img src={`http://localhost:8000/${h.portrait_path}`} alt={h.name} draggable={false} style={{ width: 100, height: 100, borderRadius: '50%', objectFit: 'cover', objectPosition: 'center 15%', border: '1px solid var(--border)' }} title={`${h.name} (Lv ${h.level} ${h.hero_class})`} />
                          <div style={{ position: 'absolute', bottom: -5, right: -5, background: 'var(--bg-dark)', border: '1px solid var(--gold)', borderRadius: '50%', width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 'bold' }}>
                            {h.birth_star}★
                          </div>
                        </div>
                        <div className="text-hi" style={{ fontSize: '0.8rem', marginTop: '0.5rem', textAlign: 'center' }}>{h.name}</div>
                        <div className="text-dim" style={{ fontSize: '0.7rem', textAlign: 'center' }}>Lv.{h.level} {h.hero_class}</div>
                      </div>
                    </div>
                  ))
                })()}
                {floorsData.base_heroes.length === 0 && <div className="text-dim text-sm">No unassigned heroes.</div>}
              </div>
            </div>

            {/* Floors */}
            <div style={{ flex: '2 1 500px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <h3 style={{ fontFamily: 'Cinzel, serif', color: 'var(--gold)', marginBottom: '0.5rem' }}>Floors</h3>
              {floorsData.floors.map(f => (
                <div key={f.floor_number} className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem' }}>
                  <div style={{ width: '80px' }}>
                    <div style={{ fontFamily: 'Cinzel, serif', color: 'var(--gold)' }}>Floor {f.floor_number}</div>
                    <div className="text-green" style={{ fontSize: '0.75rem', fontWeight: 'bold' }} title="Stat bonus per stationed hero, and bonus fatigue recovery rate">
                      +{f.stat_bonus_pct}% stats
                    </div>
                  </div>
                  <div style={{ flex: 1, display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    {/* Render assigned heroes */}
                    {f.heroes.map(h => (
                      <div key={h.id}
                           draggable
                           onDragStart={(e) => e.dataTransfer.setData('heroId', h.id)}
                           onClick={() => handleAssignFloor(h.id, null)}
                           style={{ cursor: 'grab', position: 'relative' }} title="Click, or drag back to Unassigned, to remove">
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                            <img src={`http://localhost:8000/${h.portrait_path}`} alt={h.name} draggable={false} style={{ width: 100, height: 100, borderRadius: '50%', objectFit: 'cover', objectPosition: 'center 15%', border: '1px solid var(--border)' }} />
                            <div className="text-hi" style={{ fontSize: '0.8rem', marginTop: '0.3rem', textAlign: 'center' }}>{h.name}</div>
                          </div>
                        <div style={{ position: 'absolute', top: -5, right: -5, background: 'var(--red)', color: 'white', borderRadius: '50%', width: 20, height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem' }}>&times;</div>
                      </div>
                    ))}
                    {/* Render single empty drop slot */}
                    <div onDragOver={(e) => e.preventDefault()}
                         onDrop={(e) => {
                           e.preventDefault();
                           const heroId = e.dataTransfer.getData('heroId');
                           if (heroId) {
                             handleAssignFloor(heroId, f.floor_number);
                           }
                         }}
                         style={{ 
                           width: 100, height: 100, borderRadius: '50%', 
                           border: '1px dashed var(--text-dim)', 
                           display: 'flex', alignItems: 'center', justifyContent: 'center',
                           transition: 'all 0.2s'
                         }}>
                      <span className="text-dim" style={{ fontSize: '1.5rem' }}>+</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
