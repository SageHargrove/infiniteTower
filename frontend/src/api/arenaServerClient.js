// Talks to the separately-hosted Arena server (arena_server/), not the
// player's local backend. The Arena server's address is whatever the
// player enters once in the Arena tab — there's no default because every
// host's address is different (localhost while testing, a real OpenNebula
// VM address once deployed). Stored in localStorage like other client-side
// settings (see App.jsx's soundEnabled/bgmVolume pattern).
const URL_KEY = 'arenaServerUrl'
const TOKEN_KEY = 'arenaServerToken'
const USERNAME_KEY = 'arenaServerUsername'

export function getArenaServerUrl() {
  return localStorage.getItem(URL_KEY) || ''
}

export function setArenaServerUrl(url) {
  localStorage.setItem(URL_KEY, url.replace(/\/+$/, ''))
}

export function getArenaToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getArenaUsername() {
  return localStorage.getItem(USERNAME_KEY) || ''
}

export function clearArenaSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USERNAME_KEY)
}

async function arenaRequest(path, options = {}, auth = false) {
  const base = getArenaServerUrl()
  if (!base) throw new Error('Set the Arena server address first.')
  const headers = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = getArenaToken()
    if (!token) throw new Error('Log in to the Arena server first.')
    headers['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(base + path, { headers, ...options })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Arena request failed')
  }
  return res.json()
}

export const arenaRegister = (username, password) =>
  arenaRequest('/arena/register', { method: 'POST', body: JSON.stringify({ username, password }) })

export async function arenaLogin(username, password) {
  const data = await arenaRequest('/arena/login', { method: 'POST', body: JSON.stringify({ username, password }) })
  localStorage.setItem(TOKEN_KEY, data.token)
  localStorage.setItem(USERNAME_KEY, data.username)
  return data
}

export const arenaSubmitTeam = (team) =>
  arenaRequest('/arena/submit_team', { method: 'POST', body: JSON.stringify({ team }) }, true)

export const arenaChallenge = (opponent) =>
  arenaRequest('/arena/challenge', { method: 'POST', body: JSON.stringify({ opponent }) }, true)

export const arenaMatchmake = () =>
  arenaRequest('/arena/matchmake', { method: 'POST' }, true)

export const arenaUpdateFloor = (highest_floor) =>
  arenaRequest('/arena/update_floor', { method: 'POST', body: JSON.stringify({ highest_floor }) }, true)

export const arenaLeaderboard = (limit = 20) =>
  arenaRequest(`/arena/leaderboard?limit=${limit}`)

export const arenaMyRewards = () =>
  arenaRequest('/arena/my_rewards', {}, true)

export const arenaClaimReward = (reward_id) =>
  arenaRequest('/arena/claim_reward', { method: 'POST', body: JSON.stringify({ reward_id }) }, true)

export const arenaMarketList = (hero_name, hero_class, hero_stats, hero_skills, gem_cost) =>
  arenaRequest('/arena/market/list', { method: 'POST', body: JSON.stringify({ hero_name, hero_class, hero_stats, hero_skills, gem_cost }) }, true)

export const arenaMarketGet = () =>
  arenaRequest('/arena/market', {}, true)

export const arenaMarketHire = (listing_id) =>
  arenaRequest('/arena/market/hire', { method: 'POST', body: JSON.stringify({ listing_id }) }, true)
