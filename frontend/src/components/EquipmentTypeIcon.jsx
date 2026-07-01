import React, { useState, useEffect } from 'react'

export const EQUIPMENT_ICONS = { Weapon: '⚔️', Armor: '🛡️', Accessory: '💍' }
export const WEAPON_TYPE_ICONS = { Sword: '⚔️', Spear: '🔱', Staff: '🪄', Bow: '🏹', Dagger: '🗡️' }
export const ARMOR_TYPE_ICONS = { 'Heavy Armor': '🛡️', 'Brigandine': '🦺', 'Light Armor': '🧥', 'Robe': '👘' }

export function equipmentIcon(item) {
  if (item.type === 'Weapon' && item.weapon_type) return WEAPON_TYPE_ICONS[item.weapon_type] || EQUIPMENT_ICONS.Weapon
  if (item.type === 'Armor' && item.armor_type) return ARMOR_TYPE_ICONS[item.armor_type] || EQUIPMENT_ICONS.Armor
  return EQUIPMENT_ICONS[item.type] || '❓'
}

// Buckets the 18-grade letter rarity scale (D- through Z) down to the 7
// art tiers from generated icons. D- gets "broken" (worst-condition art),
// D/D+ get "poor", SS folds into "epic" (no dedicated SS art yet).
const RARITY_ART_TIER = {
  'D-': 'broken',
  'D': 'poor', 'D+': 'poor',
  'C-': 'common', 'C': 'common', 'C+': 'common',
  'B-': 'uncommon', 'B': 'uncommon', 'B+': 'uncommon',
  'A-': 'rare', 'A': 'rare', 'A+': 'rare',
  'S-': 'epic', 'S': 'epic', 'S+': 'epic', 'SS': 'epic',
  'SSS': 'legendary', 'Z': 'legendary',
}

// Staff weapon type uses "tome" art (mage grimoire aesthetic)
const WEAPON_TYPE_SLUG = { Sword: 'sword', Spear: 'spear', Staff: 'tome', Bow: 'bow', Dagger: 'dagger' }

function typeSlug(item) {
  if (item.type === 'Weapon' && item.weapon_type) return `weapons/${WEAPON_TYPE_SLUG[item.weapon_type] || item.weapon_type.toLowerCase()}`
  if (item.type === 'Armor' && item.armor_type) return `armor/${item.armor_type.toLowerCase().replace(/ /g, '_')}`
  return null
}

function candidateSrcs(item) {
  const slug = typeSlug(item)
  if (!slug) return []
  const tier = RARITY_ART_TIER[item.rarity]
  const srcs = []
  // rarity-tiered commissioned art first, then the flat (no-tier) ComfyUI
  // generation as a fallback, then the caller falls back to the emoji.
  if (tier) srcs.push(`http://localhost:8000/static/icons/${slug}_${tier}.png`)
  srcs.push(`http://localhost:8000/static/icons/${slug}.png`)
  return srcs
}

// Tries each candidate image in order (rarity-tiered art -> flat fallback
// art -> emoji glyph) so this renders correctly regardless of which stage
// of art generation a given type/rarity has actually reached.
export function EquipmentTypeIcon({ item, fontSize = '1.5rem', glow }) {
  const srcs = candidateSrcs(item)
  const [idx, setIdx] = useState(0)

  useEffect(() => { setIdx(0) }, [item.type, item.weapon_type, item.armor_type, item.rarity])

  if (srcs.length && idx < srcs.length) {
    return (
      <img
        src={srcs[idx]}
        onError={() => setIdx(i => i + 1)}
        style={{ width: fontSize === '1.5rem' ? '28px' : '64px', height: fontSize === '1.5rem' ? '28px' : '64px', objectFit: 'contain', filter: glow ? `drop-shadow(0 0 4px ${glow})` : undefined }}
        alt=""
      />
    )
  }
  return <span style={{ fontSize, filter: glow ? `drop-shadow(0 0 4px ${glow})` : undefined }}>{equipmentIcon(item)}</span>
}
