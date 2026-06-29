import React, { useState, useEffect } from 'react'
import { getInventory, listEquipment, getFacilities, listHeroes, useItem, scrapEquipment } from '../api/client'

const EQUIPMENT_ICONS = { Weapon: '⚔️', Armor: '🛡️', Accessory: '💍' }
function equipmentIcon(item) {
  return EQUIPMENT_ICONS[item.type] || '❓'
}

const CONSUMABLE_ICONS = { potion: '🧪', scroll: '📜' }

// Equipment rarity is a 24-tier letter grade (F- through Z), a completely
// different scale than hero star rarity (1-7) — the old code reused
// var(--star${rarity}) here, which doesn't exist for a string like "C-"
// and silently fell back to an almost-invisible default color.
const RARITY_COLORS = {
  'F-': '#888888', 'F': '#999999', 'F+': '#aaaaaa',
  'E-': '#cccccc', 'E': '#dddddd', 'E+': '#eeeeee',
  'D-': '#3ddb3d', 'D': '#4dff4d', 'D+': '#6bff6b',
  'C-': '#1e90ff', 'C': '#3aa0ff', 'C+': '#5cb3ff',
  'B-': '#a83dff', 'B': '#b84dff', 'B+': '#c66bff',
  'A-': '#ffb300', 'A': '#ffc733', 'A+': '#ffd966',
  'S-': '#ff3333', 'S': '#ff5555', 'S+': '#ff7777',
  'SS': '#00ffff', 'SSS': '#66ffff', 'Z': '#ff00ff',
}
function rarityColor(rarity) {
  return RARITY_COLORS[rarity] || '#ffffff'
}

export default function InventoryPage() {
  const [loading, setLoading] = useState(true)
  const [inventory, setInventory] = useState(null)
  const [equipment, setEquipment] = useState({ equipped: [], unequipped: [] })
  const [selectedItem, setSelectedItem] = useState(null)
  const [scrapping, setScrapping] = useState(false)
  const [heroes, setHeroes] = useState([])
  const [useTargetId, setUseTargetId] = useState('')
  const [using, setUsing] = useState(false)
  const [useMessage, setUseMessage] = useState(null)

  const [vaultCapacity, setVaultCapacity] = useState(20)

  const [showJunk, setShowJunk] = useState(false)

  useEffect(() => { refresh() }, [showJunk])

  async function refresh() {
    setLoading(true)
    try {
      const [inv, eq, facs, heroList] = await Promise.all([
        getInventory(),
        listEquipment(showJunk),
        getFacilities().catch(() => null),
        listHeroes(true).catch(() => [])
      ])
      setInventory(inv || [])
      setEquipment(eq || { equipped: [], unequipped: [] })
      setHeroes(heroList || [])
      
      let capacity = 20
      if (facs && facs.built) {
        const vault = facs.built.find(f => f.type === 'Vault')
        if (vault) {
          capacity = 20 + (vault.slots_unlocked * 16) // Scales: 36, 52, 68, 84, 100
        }
      }
      setVaultCapacity(capacity)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const [filter, setFilter] = useState('All')
  const [rarityFilter, setRarityFilter] = useState(new Set())
  const [hideEquipped, setHideEquipped] = useState(false)
  const [bulkScrapping, setBulkScrapping] = useState(false)
  const [multiSelectMode, setMultiSelectMode] = useState(false)
  const [selectedItems, setSelectedItems] = useState(new Set())

  const toggleRarity = (r) => {
    setRarityFilter(prev => {
      const next = new Set(prev);
      if (next.has(r)) next.delete(r);
      else next.add(r);
      return next;
    });
  }

  // Combine items for grid display
  let allItems = []
  if (Array.isArray(inventory)) {
    inventory.forEach(item => {
      if (item.item_type === 'potion' || item.item_type === 'scroll') {
        allItems.push({ ...item, typeId: (item.item_type === 'potion' ? 'pot_' : 'scr_') + item.item_name, itemType: 'consumable' })
      } else {
        allItems.push({ ...item, typeId: 'mat_' + item.item_name, itemType: 'material' })
      }
    })
  }
  if (equipment.unequipped) {
    equipment.unequipped.forEach(eq => allItems.push({ ...eq, typeId: 'eq_' + eq.id, itemType: 'equipment', isEquipped: false }))
  }
  if (equipment.equipped) {
    equipment.equipped.forEach(eq => allItems.push({ ...eq, typeId: 'eq_' + eq.id, itemType: 'equipment', isEquipped: true }))
  }

  allItems = allItems.filter(item => {
    let typeMatch = false;
    if (filter === 'All') typeMatch = true;
    else if (filter === 'Materials') typeMatch = item.itemType === 'material';
    else if (filter === 'Consumables') typeMatch = item.itemType === 'consumable';
    else if (filter === 'Equipment') typeMatch = item.itemType === 'equipment';
    else if (item.itemType === 'equipment' && filter === item.type) typeMatch = true;
    
    if (!typeMatch) return false;
    
    if (item.itemType === 'equipment' && rarityFilter.size > 0) {
      if (!rarityFilter.has(item.rarity)) return false;
    }

    if (hideEquipped && item.itemType === 'equipment' && item.isEquipped) return false;

    return true;
  });

  // Select first item by default if none selected
  useEffect(() => {
    if (!loading && !selectedItem && allItems.length > 0) {
      setSelectedItem(allItems[0])
    }
  }, [loading, filter, allItems.length, selectedItem])

  if (loading) return <div className="page text-dim">Loading Vault...</div>

  // Pad the grid based on Vault capacity
  const minSlots = vaultCapacity
  const slots = [...allItems]
  while (slots.length < minSlots) {
    slots.push(null)
  }

  const handleBulkScrap = async () => {
    if (!window.confirm(`Are you sure you want to scrap ALL UNEQUIPPED ${filter === 'All' ? 'Equipment' : filter}? This cannot be undone.`)) return;
    setBulkScrapping(true);
    try {
      const toScrap = allItems.filter(i => i.itemType === 'equipment' && !i.isEquipped);
      for (const item of toScrap) {
        await scrapEquipment(item.id);
      }
      refresh();
      setSelectedItem(null);
    } catch (e) {
      console.error(e);
      alert('Error during bulk scrap: ' + e.message);
    } finally {
      setBulkScrapping(false);
    }
  };

  return (
    <div className="page" style={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      <div className="section-header" style={{ marginBottom: '1.5rem', fontFamily: 'Cinzel, serif', fontSize: '2rem', textShadow: '0 0 10px rgba(255,255,255,0.2)' }}>Vault</div>
      
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', alignItems: 'center' }}>
        {['All', 'Equipment', 'Weapon', 'Armor', 'Accessory', 'Materials', 'Consumables'].map(f => (
          <button key={f} className={`btn ${filter === f ? 'btn-primary' : ''}`} onClick={() => { 
            setFilter(f); 
            setSelectedItem(null); 
            setSelectedItems(new Set());
          }}>{f}</button>
        ))}
        {['Equipment', 'Weapon', 'Armor', 'Accessory'].includes(filter) && (
          <button className="btn" style={{ marginLeft: 'auto', background: 'var(--red)', color: 'white' }} onClick={handleBulkScrap} disabled={bulkScrapping}>
            {bulkScrapping ? 'Scrapping...' : `Bulk Scrap Unequipped ${filter}`}
          </button>
        )}
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', alignItems: 'center' }}>
        <button 
          className={`btn ${multiSelectMode ? 'btn-gold' : ''}`}
          onClick={() => {
            setMultiSelectMode(!multiSelectMode);
            setSelectedItems(new Set());
            setSelectedItem(null);
          }}
        >
          {multiSelectMode ? 'Cancel Multi-Select' : 'Enable Multi-Select'}
        </button>

        {multiSelectMode && selectedItems.size > 0 && (
          <button 
            className="btn" 
            style={{ background: 'var(--red)', color: 'white' }}
            disabled={bulkScrapping}
            onClick={async () => {
              if (!window.confirm(`Scrap ${selectedItems.size} selected items?`)) return;
              setBulkScrapping(true);
              try {
                const toScrap = allItems.filter(i => selectedItems.has(i.typeId) && i.itemType === 'equipment' && !i.isEquipped);
                for (const item of toScrap) {
                  await scrapEquipment(item.id);
                }
                refresh();
                setSelectedItems(new Set());
              } catch (e) {
                console.error(e);
                alert('Error: ' + e.message);
              } finally {
                setBulkScrapping(false);
              }
            }}
          >
            {bulkScrapping ? 'Scrapping...' : `Scrap ${selectedItems.size} Selected Items`}
          </button>
        )}
      </div>

      {['All', 'Equipment', 'Weapon', 'Armor', 'Accessory'].includes(filter) && (
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="text-dim" style={{ fontSize: '0.9rem', marginRight: '0.5rem' }}>Filter by Rarity (Multi-select):</span>
          {['Z', 'SSS', 'SS', 'S+', 'S', 'S-', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-'].map(r => (
            <button 
              key={r} 
              className={`btn ${rarityFilter.has(r) ? 'btn-gold' : ''}`} 
              style={{ padding: '0.2rem 0.5rem', fontSize: '0.8rem', border: rarityFilter.has(r) ? `1px solid ${rarityColor(r)}` : '1px solid var(--border)' }}
              onClick={() => { toggleRarity(r); setSelectedItem(null); setSelectedItems(new Set()); }}
            >
              {r}
            </button>
          ))}
          {rarityFilter.size > 0 && (
            <button className="btn" style={{ padding: '0.2rem 0.5rem', fontSize: '0.8rem', marginLeft: '0.5rem' }} onClick={() => { setRarityFilter(new Set()); setSelectedItems(new Set()); }}>Clear Rarities</button>
          )}
          <button
            className={`btn ${hideEquipped ? 'btn-gold' : ''}`}
            style={{ padding: '0.2rem 0.5rem', fontSize: '0.8rem', marginLeft: 'auto' }}
            onClick={() => setHideEquipped(s => !s)}
            title="Only show equipment nobody currently has equipped."
          >
            {hideEquipped ? 'Showing Unequipped Only' : 'Show Unequipped Only'}
          </button>
          <button
            className={`btn ${showJunk ? 'btn-gold' : ''}`}
            style={{ padding: '0.2rem 0.5rem', fontSize: '0.8rem' }}
            onClick={() => setShowJunk(s => !s)}
            title="F-grade starter weapons left over after upgrading a hero's gear are hidden by default."
          >
            {showJunk ? 'Hide Starter Gear' : 'Show Starter Gear'}
          </button>
        </div>
      )}

      <div style={{ display: 'flex', gap: '2rem', flex: 1, minHeight: 0 }}>
        
        {/* Left Side: The Grid */}
        <div className="card" style={{ flex: 2, display: 'flex', flexDirection: 'column', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border)', padding: '1.5rem', overflowY: 'auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(64px, 1fr))', gap: '8px', alignContent: 'start' }}>
            {slots.map((item, index) => {
              const isSelected = item && (multiSelectMode ? selectedItems.has(item.typeId) : (selectedItem && item.typeId === selectedItem.typeId));
              const isEmpty = !item;
              let bgColor = 'rgba(255,255,255,0.02)'
              let borderColor = 'var(--border)'
              let content = null

              if (item) {
                if (item.itemType === 'material') {
                  borderColor = 'var(--border-hi)'
                  content = <span style={{ fontSize: '1.5rem' }}>📦</span>
                } else if (item.itemType === 'potion' || item.itemType === 'scroll') {
                  borderColor = item.itemType === 'potion' ? 'var(--green)' : '#a83dff'
                  content = <span style={{ fontSize: '1.5rem' }}>{CONSUMABLE_ICONS[item.itemType]}</span>
                } else if (item.itemType === 'equipment') {
                  borderColor = rarityColor(item.rarity)
                  bgColor = `rgba(255,255,255,0.05)`
                  content = <span style={{ fontSize: '1.5rem', filter: `drop-shadow(0 0 4px ${rarityColor(item.rarity)})` }}>{equipmentIcon(item)}</span>
                }
              }

              return (
                <div
                  key={item ? item.typeId : `empty-${index}`}
                  className={isSelected ? 'vault-item-selected' : ''}
                  onClick={() => {
                    if (!item) return;
                    if (multiSelectMode) {
                      setSelectedItems(prev => {
                        const next = new Set(prev);
                        if (next.has(item.typeId)) next.delete(item.typeId);
                        else next.add(item.typeId);
                        return next;
                      });
                    } else {
                      setSelectedItem(item);
                    }
                  }}
                  style={{ 
                    aspectRatio: '1/1', 
                    background: bgColor, 
                    border: `2px solid ${borderColor}`,
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                    cursor: isEmpty ? 'default' : 'pointer',
                    boxShadow: item ? `inset 0 0 15px ${borderColor}20` : 'none',
                    transition: 'all 0.1s ease',
                    opacity: isEmpty ? 0.3 : 1
                  }}
                  onMouseEnter={(e) => { if (item) e.currentTarget.style.transform = 'scale(1.05)'; }}
                  onMouseLeave={(e) => { if (item) e.currentTarget.style.transform = 'scale(1)'; }}
                >
                  {content}
                  
                  {/* Quantity Badge */}
                  {item && (item.itemType === 'material' || item.itemType === 'potion' || item.itemType === 'scroll') && (
                    <div style={{ position: 'absolute', bottom: -2, right: -2, background: 'var(--bg)', border: '1px solid var(--border-hi)', fontSize: '0.7rem', padding: '0 4px', borderRadius: 4, fontFamily: 'monospace', fontWeight: 'bold' }}>
                      {item.quantity}
                    </div>
                  )}

                  {/* Equipped Indicator */}
                  {item && item.isEquipped && (
                    <div style={{ position: 'absolute', top: -4, left: -4, fontSize: '1rem', filter: 'drop-shadow(0 0 2px black)' }}>
                      E
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Right Side: Details Panel */}
        <div className="card" style={{ flex: 1, minWidth: '300px', display: 'flex', flexDirection: 'column', padding: '2rem', background: 'rgba(0,0,0,0.6)', border: '1px solid var(--gold-dim)' }}>
          {!selectedItem ? (
            <div className="text-dim" style={{ margin: 'auto', textAlign: 'center', fontStyle: 'italic', fontSize: '1.1rem' }}>
              Select an item to view details.
            </div>
          ) : (
            <>
              {selectedItem.itemType === 'material' && (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ fontSize: '4rem', textAlign: 'center', marginBottom: '1rem', filter: 'drop-shadow(0 0 20px rgba(255,255,255,0.2))' }}>📦</div>
                  <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.8rem', textAlign: 'center', color: 'var(--text-hi)', textTransform: 'capitalize', borderBottom: '1px solid var(--border)', paddingBottom: '1rem', marginBottom: '1rem' }}>
                    {selectedItem.item_name.replace('_', ' ')}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div className="text-dim" style={{ fontSize: '1.1rem', marginBottom: '1.5rem', textAlign: 'center', lineHeight: '1.5' }}>
                      A fundamental material used in the Hollow Spire.<br/>Can be used for crafting and base upgrades.
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.05)', padding: '1rem', borderRadius: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="text-dim" style={{ fontSize: '1.2rem', textTransform: 'uppercase', letterSpacing: '2px' }}>Amount Owned</span>
                      <span className="text-gold" style={{ fontSize: '1.8rem', fontFamily: 'Cinzel, serif', fontWeight: 'bold' }}>{selectedItem.quantity}</span>
                    </div>
                  </div>
                </div>
              )}

              {(selectedItem.itemType === 'potion' || selectedItem.itemType === 'scroll') && (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ fontSize: '4rem', textAlign: 'center', marginBottom: '1rem' }}>{CONSUMABLE_ICONS[selectedItem.itemType]}</div>
                  <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.8rem', textAlign: 'center', color: 'var(--text-hi)', borderBottom: '1px solid var(--border)', paddingBottom: '1rem', marginBottom: '1rem' }}>
                    {selectedItem.item_name}
                  </div>
                  <div className="text-dim" style={{ fontSize: '1.05rem', marginBottom: '1.5rem', textAlign: 'center', lineHeight: '1.5' }}>
                    {selectedItem.description}
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.05)', padding: '1rem', borderRadius: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <span className="text-dim" style={{ fontSize: '1.1rem', textTransform: 'uppercase', letterSpacing: '2px' }}>Owned</span>
                    <span className="text-gold" style={{ fontSize: '1.6rem', fontFamily: 'Cinzel, serif', fontWeight: 'bold' }}>{selectedItem.quantity}</span>
                  </div>

                  <div style={{ marginTop: 'auto' }}>
                    <select
                      className="input"
                      value={useTargetId}
                      onChange={e => setUseTargetId(e.target.value)}
                      style={{ width: '100%', marginBottom: '0.8rem', padding: '0.6rem' }}
                    >
                      <option value="">Select a hero...</option>
                      {heroes.map(h => (
                        <option key={h.id} value={h.id}>{h.name} (Lv.{h.level})</option>
                      ))}
                    </select>
                    <button
                      className="btn btn-gold"
                      style={{ width: '100%', padding: '0.8rem' }}
                      disabled={!useTargetId || using}
                      onClick={async () => {
                        setUsing(true)
                        setUseMessage(null)
                        try {
                          await useItem(selectedItem.item_name, Number(useTargetId))
                          setUseMessage('Used!')
                          await refresh()
                          setSelectedItem(null)
                        } catch (e) {
                          setUseMessage(e.message)
                        } finally {
                          setUsing(false)
                        }
                      }}
                    >
                      {using ? 'Using...' : 'Use'}
                    </button>
                    {useMessage && (
                      <div className="text-dim text-center" style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>{useMessage}</div>
                    )}
                  </div>
                </div>
              )}

              {selectedItem.itemType === 'equipment' && (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ fontSize: '4rem', textAlign: 'center', marginBottom: '1rem', filter: `drop-shadow(0 0 20px ${rarityColor(selectedItem.rarity)})` }}>
                    {equipmentIcon(selectedItem)}
                  </div>
                  
                  <div style={{ fontFamily: 'Cinzel, serif', fontSize: '1.8rem', textAlign: 'center', color: rarityColor(selectedItem.rarity), borderBottom: `1px solid ${rarityColor(selectedItem.rarity)}`, paddingBottom: '0.5rem', marginBottom: '0.2rem', textShadow: `0 0 10px ${rarityColor(selectedItem.rarity)}` }}>
                    {selectedItem.name}
                  </div>
                  <div style={{ textAlign: 'center', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '3px', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                    {selectedItem.rarity}★ {selectedItem.type}
                  </div>

                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                    {[
                      ['Strength', selectedItem.base_str, v => `+${v}`],
                      ['Intelligence', selectedItem.base_int, v => `+${v}`],
                      ['Endurance', selectedItem.base_end, v => `+${v}`],
                      ['Max Health', selectedItem.base_hlt, v => `+${v}`],
                      ['Agility', selectedItem.base_agi, v => `+${v}`],
                      ['Willpower', selectedItem.base_wil, v => `+${v}`],
                      ['Luck', selectedItem.base_luck, v => `+${v}`],
                      ['Strength %', selectedItem.str_pct, v => `+${(v * 100).toFixed(0)}%`],
                      ['Intelligence %', selectedItem.int_pct, v => `+${(v * 100).toFixed(0)}%`],
                      ['Max Health %', selectedItem.hlt_pct, v => `+${(v * 100).toFixed(0)}%`],
                      ['Agility %', selectedItem.agi_pct, v => `+${(v * 100).toFixed(0)}%`],
                      ['Crit Chance', selectedItem.crit_chance, v => `+${(v * 100).toFixed(0)}%`],
                      ['Dodge Chance', selectedItem.dodge_chance, v => `+${(v * 100).toFixed(0)}%`],
                      ['Armor Penetration', selectedItem.armor_pen, v => `+${(v * 100).toFixed(0)}%`],
                      ['Damage Reduction', selectedItem.dmg_reduction_pct, v => `+${(v * 100).toFixed(0)}%`],
                    ].filter(([, val]) => val > 0).map(([label, val, fmt]) => (
                      <div key={label} style={{ display: 'flex', justifyContent: 'space-between', background: 'rgba(201,168,76,0.1)', padding: '0.8rem 1rem', borderRadius: 4 }}>
                        <span className="text-dim">{label}</span>
                        <span className="text-gold" style={{ fontFamily: 'Cinzel, serif', fontSize: '1.2rem' }}>{fmt(val)}</span>
                      </div>
                    ))}
                    {[selectedItem.base_str, selectedItem.base_int, selectedItem.base_end, selectedItem.base_hlt, selectedItem.base_agi,
                      selectedItem.base_wil, selectedItem.base_luck,
                      selectedItem.str_pct, selectedItem.int_pct, selectedItem.hlt_pct, selectedItem.agi_pct,
                      selectedItem.crit_chance, selectedItem.dodge_chance, selectedItem.armor_pen, selectedItem.dmg_reduction_pct
                    ].every(v => !v) && (
                      <div className="text-dim" style={{ fontStyle: 'italic', textAlign: 'center', padding: '1rem' }}>No bonus stats.</div>
                    )}
                  </div>

                  <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
                    {selectedItem.isEquipped ? (
                      <div style={{ textAlign: 'center', color: 'var(--green)', padding: '1rem', background: 'rgba(74,154,106,0.1)', borderRadius: 4 }}>
                        Equipped to Hero #{selectedItem.is_equipped_to}
                      </div>
                    ) : (
                      <>
                        <div className="text-dim text-center" style={{ fontSize: '0.9rem', fontStyle: 'italic', marginBottom: '0.8rem' }}>
                          Can be equipped from the Heroes menu.
                        </div>
                        <button
                          className="btn"
                          style={{ width: '100%', padding: '0.6rem', border: '1px solid #c87030', color: '#c87030', background: 'rgba(200,112,48,0.08)' }}
                          disabled={scrapping}
                          onClick={async () => {
                            if (!confirm(`Scrap ${selectedItem.name}? This destroys the item permanently in exchange for crafting materials.`)) return
                            setScrapping(true)
                            try {
                              await scrapEquipment(selectedItem.id)
                              setSelectedItem(null)
                              await refresh()
                            } catch (e) {
                              alert(e.message)
                            } finally {
                              setScrapping(false)
                            }
                          }}
                        >
                          {scrapping ? 'Scrapping...' : '⚒ Scrap for Materials'}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
