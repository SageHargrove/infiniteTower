import { emitToast } from '../toastBus'

const BASE = ''

// Every reward-granting endpoint in this codebase uses a slightly different
// response shape (flat gold_gained/gems_gained on tower floors, {type,
// reward} on daily dungeons, {effects:{...}} on event/explore resolution,
// {equipment:{...}} on forge crafting). Rather than wire a toast call into
// every individual call site (and inevitably miss one — see the gems display
// bug), every response funnels through here once, so nothing can silently
// fail to surface again.
function extractRewards(data) {
  if (!data || typeof data !== 'object') return null
  const gold = (data.gold_gained || 0) + (data.effects?.gold || 0) + (data.type === 'gold' ? (data.reward || 0) : 0)
  const gems = (data.gems_gained || 0) + (data.effects?.gems || 0)
  const supplies = (data.supplies_gained || 0) + (data.type === 'supplies' ? (data.reward || 0) : 0)
  const materials = { ...(data.materials_gained || {}) }
  if (data.type === 'materials' && data.reward && typeof data.reward === 'object') {
    for (const [k, v] of Object.entries(data.reward)) materials[k] = (materials[k] || 0) + v
  }
  const equipment = data.equipment_drop || data.equipment || null
  const relic = data.relic_drop || null

  const lines = []
  if (gold > 0) lines.push({ label: 'Gold', value: `+${gold.toLocaleString()}`, color: 'var(--gold)' })
  if (gems > 0) lines.push({ label: 'Gems', value: `+${gems.toLocaleString()}`, color: '#00ffff' })
  if (supplies > 0) lines.push({ label: 'Supplies', value: `+${supplies.toLocaleString()}`, color: 'var(--text-hi)' })
  for (const [name, qty] of Object.entries(materials)) {
    if (qty > 0) lines.push({ label: name, value: `+${qty}`, color: 'var(--text-hi)' })
  }
  if (equipment?.name) lines.push({ label: 'Equipment', value: equipment.name, color: 'var(--green)' })
  if (relic?.name) lines.push({ label: relic.relic_type === 'rune' ? 'Rune' : 'Seal', value: relic.name, color: '#c060ff' })

  return lines.length ? lines : null
}

// These already reveal their own rewards through dedicated, properly-paced
// UI (the post-combat screen, event/explore resolution panels) — the
// generic toast below would otherwise fire the instant the response lands,
// which for floor/enter means "before the player has even watched the
// fight play out."
const SKIP_AUTO_TOAST_PATHS = ['/tower/floor/enter', '/tower/floor/event/resolve', '/tower/floor/explore/resolve']

async function request(path, options = {}) {
  const isGet = !options.method || options.method === 'GET'
  const url = isGet ? BASE + path + (path.includes('?') ? '&' : '?') + 't=' + Date.now() : BASE + path
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    let msg = err.detail || err.error || 'Request failed'
    if (typeof msg === 'object') msg = JSON.stringify(msg)
    throw new Error(msg)
  }
  const data = await res.json()
  const skipToast = SKIP_AUTO_TOAST_PATHS.some(p => path.startsWith(p))
  const lines = skipToast ? null : extractRewards(data)
  if (lines) emitToast({ title: 'Rewards', lines, borderColor: 'var(--gold)' })
  if (Array.isArray(data?.ego_rebellions) && data.ego_rebellions.length) {
    for (const reb of data.ego_rebellions) {
      emitToast({
        title: '⚡ Ego Rebellion',
        lines: [{ label: reb.hero_name, value: reb.message, color: '#ff8888' }],
        borderColor: '#ff4444',
      })
    }
  }
  return data
}

export const getChatLogs = (limit = 10) => request(`/chat/?limit=${limit}`)
export const egoAutoTeam = (teamId, egoHeroId) => request('/heroes/team/ego_auto', { method: 'POST', body: JSON.stringify({ team_id: teamId, ego_hero_id: egoHeroId }) })
export const getEgoRecommendation = (heroId) => request(`/heroes/${heroId}/ego_recommendation`)

// Base
export const getBase = () => request('/base/')
export const renameBase = (name) => request('/base/rename', { method: 'POST', body: JSON.stringify({ name }) })
export const setMasterName = (name) => request('/base/master-name', { method: 'POST', body: JSON.stringify({ name }) })
export const completeTutorial = () => request('/base/tutorial/complete', { method: 'POST' })
export const upgradeBase = () => request('/base/upgrade', { method: 'POST' })
export const restHeroes = () => request('/base/rest', { method: 'POST' })
export const runDailyDungeon = (type) => request(`/base/daily_dungeon/${type}`, { method: 'POST' })
export const getBaseFloors = () => request('/base/floors')
export const assignBaseFloor = (heroId, floor) => request('/base/floors/assign', { method: 'POST', body: JSON.stringify({ hero_id: heroId, floor }) })

export const getFacilities = () => request('/base/facilities')
export const buildFacility = (type) => request('/base/facilities/build', { method: 'POST', body: JSON.stringify({ facility_type: type }) })
export const assignFacility = (facId, heroId) => request('/base/facilities/assign', { method: 'POST', body: JSON.stringify({ facility_id: facId, hero_id: heroId }) })
export const removeFacility = (heroId) => request('/base/facilities/remove', { method: 'POST', body: JSON.stringify({ hero_id: heroId }) })
export const upgradeFacility = (facilityId) => request('/base/facilities/upgrade', { method: 'POST', body: JSON.stringify({ facility_id: facilityId }) })
export const configTraining = (facilityId, heroId, role, targetSkillId, targetHeroId) => request('/base/facilities/training-config', { method: 'POST', body: JSON.stringify({ facility_id: facilityId, hero_id: heroId, role, target_skill_id: targetSkillId, target_hero_id: targetHeroId }) })
export const getMageTowerUpgrades = () => request('/base/facilities/mage-tower/upgrades')
export const buyResearchUpgrade = (upgradeId) => request('/base/facilities/mage-tower/buy', { method: 'POST', body: JSON.stringify({ upgrade_id: upgradeId }) })

export const getBaseUpgrades = () => request('/base/upgrades')
export const buyBaseUpgrade = (upgradeId) => request('/base/upgrades/purchase', { method: 'POST', body: JSON.stringify({ upgrade_id: upgradeId }) })

export const grantResources = (gold = 0, gems = 0, supplies = 0) => request('/base/dev/grant', { method: 'POST', body: JSON.stringify({ gold, gems, supplies }) })
export const clearDevInventory = () => request('/base/dev/clear-inventory', { method: 'POST' })
export const setDevLevel = (heroId, level) => request('/base/dev/set-level', { method: 'POST', body: JSON.stringify({ hero_id: heroId, level }) })
export const grantInventoryItem = (itemName, itemType, quantity = 1) => request(`/base/inventory/add?item_name=${encodeURIComponent(itemName)}&item_type=${encodeURIComponent(itemType)}&quantity=${quantity}`, { method: 'POST' })

export const listUpgrades = () => request('/base/upgrades')
export const purchaseUpgrade = (facilityId) => request('/base/upgrades/purchase', { method: 'POST', body: JSON.stringify({ upgrade_id: facilityId }) })
export const getInventory = () => request('/base/inventory')
export const useItem = (itemName, heroId, targetSkillId = null) => request('/base/inventory/use', { method: 'POST', body: JSON.stringify({ item_name: itemName, hero_id: heroId, target_skill_id: targetSkillId }) })

// Heroes
export const listHeroes = (aliveOnly = false) => request(`/heroes/?alive_only=${aliveOnly}`)
export const getHero = (id) => request(`/heroes/${id}`)
export const setTeam = (teamId, heroIds) => request('/heroes/team/set', { method: 'POST', body: JSON.stringify({ team_id: teamId, hero_ids: heroIds }) })
export const removeHeroFromTeam = (heroId) => request(`/heroes/${heroId}/remove-from-team`, { method: 'POST' })
export const reorderTeam = (teamId, heroIds) => request('/heroes/team/reorder', { method: 'POST', body: JSON.stringify({ team_id: teamId, hero_ids: heroIds }) })
export const getTeam = (teamId = 1) => request(`/heroes/team/${teamId}`)
export const getAllTeams = () => request('/heroes/teams/all')
export const assignTeamLeader = (heroId) => request('/heroes/team/assign-leader', { method: 'POST', body: JSON.stringify({ hero_id: heroId }) })
export const getLeaderRecommendation = (teamId) => request(`/heroes/team/${teamId}/leader-recommendation`)
export const dismissHero = (id) => request(`/heroes/${id}`, { method: 'DELETE' })
export const dismissHeroesBulk = (heroIds) => request('/heroes/dismiss-bulk', { method: 'POST', body: JSON.stringify({ hero_ids: heroIds }) })
export const synthesizeHero = (targetId, sacrificeId) => request('/heroes/synthesize', { method: 'POST', body: JSON.stringify({ target_id: targetId, sacrifice_id: sacrificeId }) })
export const ascendHero = (heroId) => request(`/heroes/${heroId}/ascend`, { method: 'POST' })
export const getAscensionInfo = (heroId) => request(`/heroes/${heroId}/ascension-info`)
export const promoteHero = (heroId) => request(`/heroes/${heroId}/promote`, { method: 'POST' })
export const regeneratePortraits = () => request('/heroes/regenerate-portraits', { method: 'POST' })
export const craftMaterialEquipment = (material, targetClass) => request('/base/craft-equipment', { method: 'POST', body: JSON.stringify({ material, target_class: targetClass }) })
export const craftBandages = (crafterId, quantity = 1) => request('/base/infirmary/craft-bandages', { method: 'POST', body: JSON.stringify({ crafter_id: crafterId, quantity }) })
export const getMarketCatalog = () => request('/base/market/catalog')
export const purchaseMarketItem = (itemId) => request('/base/market/purchase', { method: 'POST', body: JSON.stringify({ item_id: itemId }) })
export const evolveHero = (heroId, targetClass) => request(`/heroes/${heroId}/evolve`, { method: 'POST', body: JSON.stringify({ target_class: targetClass }) })
export const getClassEvolutions = () => request('/heroes/classes/evolutions')
export const getLegacies = () => request('/heroes/legacies')
export const regenerateProfile = (heroId) => request(`/heroes/${heroId}/regenerate-profile`, { method: 'POST' })
export const getHeroAptitudes = (heroId) => request(`/heroes/${heroId}/aptitudes`)
export const getBonds = () => request('/heroes/bonds')

// Equipment
export const listEquipment = () => request('/equipment/')
export const craftEquipment = (crafterId) => request('/equipment/craft', { method: 'POST', body: JSON.stringify({ crafter_id: crafterId }) })
export const equipItem = (equipmentId, heroId) => request('/equipment/equip', { method: 'POST', body: JSON.stringify({ equipment_id: equipmentId, hero_id: heroId }) })
export const unequipItem = (equipmentId) => request('/equipment/unequip', { method: 'POST', body: JSON.stringify({ equipment_id: equipmentId }) })
export const scrapEquipment = (equipmentId) => request('/equipment/scrap', { method: 'POST', body: JSON.stringify({ equipment_id: equipmentId }) })

export const equipConsumable = (heroId, itemName) => request('/base/heroes/equip-consumable', { method: 'POST', body: JSON.stringify({ hero_id: heroId, item_name: itemName }) })

// Gacha
export const pullHeroes = (count = 1, usePortrait = false, currency = 'gem') => request('/gacha/pull', { method: 'POST', body: JSON.stringify({ count, use_portrait: usePortrait, currency }) })
export const pullEquipment = (count = 1, currency = 'gold') => request('/gacha/equipment-pull', { method: 'POST', body: JSON.stringify({ count, currency }) })
export const getOdds = (currency = 'gem') => request(`/gacha/odds?currency=${currency}`)
export const getEquipmentOdds = (currency = 'gold') => request(`/gacha/equipment-odds?currency=${currency}`)
export const getPityInfo = () => request('/gacha/pity-info')
export const redeemSpark = () => request('/gacha/spark-redeem', { method: 'POST' })
export const redeemEquipSpark = () => request('/gacha/equip-spark-redeem', { method: 'POST' })

// Tower / Runs
export const enterFloor = (floorNumber, teamIds) => request('/tower/floor/enter', { method: 'POST', body: JSON.stringify({ floor_number: floorNumber, team_ids: Array.isArray(teamIds) ? teamIds : [teamIds] }) })
export const getNarrative = (narrativeId) => request(`/tower/narrative/${narrativeId}`)
export const previewFloor = (floorNumber) => request(`/tower/floor/preview/${floorNumber}`)
export const resolveEvent = (floorNumber, teamId, templateId, choiceId, theme) => request('/tower/floor/event/resolve', { method: 'POST', body: JSON.stringify({ floor_number: floorNumber, team_id: teamId, template_id: templateId, choice_id: choiceId, theme: theme }) })
export const resolveExplore = (floorNumber, teamId, choiceId) => request('/tower/floor/explore/resolve', { method: 'POST', body: JSON.stringify({ floor_number: floorNumber, team_id: teamId, choice_id: choiceId }) })
export const listRuns = () => request('/runs/')
export const getEventLog = (runId = null, limit = 50) => request(`/runs/log?${runId ? `run_id=${runId}&` : ''}limit=${limit}`)

// Arena (local backend side only — resolves a team's full combat stats
// exactly like a Tower floor would, for shipping to the separate Arena
// server. See api/arenaServerClient.js for the remote-host calls.)
export const getArenaSnapshot = (teamId) => request(`/arena/team/${teamId}/snapshot`)

// Profiles
export const listProfiles = () => request('/profiles/')
export const switchProfile = (name) => request('/profiles/switch', { method: 'POST', body: JSON.stringify({ name }) })
export const renameProfile = (oldName, newName) => request('/profiles/rename', { method: 'POST', body: JSON.stringify({ old_name: oldName, new_name: newName }) })
export const deleteProfile = (name) => request('/profiles/delete', { method: 'POST', body: JSON.stringify({ name }) })

// Portrait Cache
