let audioCtx = null
let bgmOscillators = []
let soundEnabled = localStorage.getItem('soundEnabled') !== 'false'
let globalBgmVolume = parseFloat(localStorage.getItem('bgmVolume') || '0.5')
let globalSfxVolume = parseFloat(localStorage.getItem('sfxVolume') || '0.5')

export function setSoundEnabled(enabled) {
  soundEnabled = enabled
  localStorage.setItem('soundEnabled', enabled)
  if (!enabled) {
    stopBgm()
  } else {
    playBgm()
  }
}

export function isSoundEnabled() {
  return soundEnabled
}

export function setBgmVolume(vol) {
  globalBgmVolume = vol
  localStorage.setItem('bgmVolume', vol)
  if (bgmAudio) {
    bgmAudio.volume = globalBgmVolume
  }
}

export function setSfxVolume(vol) {
  globalSfxVolume = vol
  localStorage.setItem('sfxVolume', vol)
}

export function initAudio() {
  if (audioCtx) {
    if (audioCtx.state === 'suspended') audioCtx.resume()
    return
  }
  try {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    
    // Ensure it resumes on any user interaction
    const resumeAudio = () => {
      if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume()
      }
      document.removeEventListener('click', resumeAudio)
    }
    document.addEventListener('click', resumeAudio)

    if (soundEnabled) {
      if (audioCtx.state === 'suspended') audioCtx.resume()
      playBgm()
    }
  } catch (e) {
    console.error("Web Audio API not supported", e)
  }
}

export function playClick() {
  if (!soundEnabled || !audioCtx) return
  if (globalSfxVolume === 0) return
  if (audioCtx.state === 'suspended') audioCtx.resume()

  const osc = audioCtx.createOscillator()
  const gain = audioCtx.createGain()
  
  osc.type = 'sine'
  osc.frequency.setValueAtTime(800, audioCtx.currentTime)
  osc.frequency.exponentialRampToValueAtTime(1200, audioCtx.currentTime + 0.05)
  
  gain.gain.setValueAtTime(0.02 * globalSfxVolume, audioCtx.currentTime)
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.05)
  
  osc.connect(gain)
  gain.connect(audioCtx.destination)
  
  osc.start()
  osc.stop(audioCtx.currentTime + 0.05)
}

// kind: 'melee' | 'caster' | 'ranged' | 'enemy' — a rough archetype bucket
// derived from the attacker's existing power_stat/is_ranged combat fields
// (see CombatArena's classifyAttacker), not a separate per-class sound list.
export function playHitSound(kind, isCrit = false) {
  if (!soundEnabled || !audioCtx) return
  if (globalSfxVolume === 0) return
  if (audioCtx.state === 'suspended') audioCtx.resume()

  const osc = audioCtx.createOscillator()
  const gain = audioCtx.createGain()
  const vol = (isCrit ? 0.05 : 0.03) * globalSfxVolume
  const now = audioCtx.currentTime

  if (kind === 'caster') {
    osc.type = 'sine'
    osc.frequency.setValueAtTime(isCrit ? 1100 : 900, now)
    osc.frequency.exponentialRampToValueAtTime(isCrit ? 1900 : 1400, now + 0.12)
    gain.gain.setValueAtTime(vol, now)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18)
    osc.connect(gain); gain.connect(audioCtx.destination)
    osc.start(); osc.stop(now + 0.18)
  } else if (kind === 'ranged') {
    osc.type = 'triangle'
    osc.frequency.setValueAtTime(700, now)
    osc.frequency.exponentialRampToValueAtTime(200, now + 0.08)
    gain.gain.setValueAtTime(vol, now)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.09)
    osc.connect(gain); gain.connect(audioCtx.destination)
    osc.start(); osc.stop(now + 0.09)
  } else if (kind === 'enemy') {
    osc.type = 'sawtooth'
    osc.frequency.setValueAtTime(150, now)
    osc.frequency.exponentialRampToValueAtTime(90, now + 0.1)
    gain.gain.setValueAtTime(vol, now)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12)
    osc.connect(gain); gain.connect(audioCtx.destination)
    osc.start(); osc.stop(now + 0.12)
  } else { // melee
    osc.type = 'square'
    osc.frequency.setValueAtTime(isCrit ? 320 : 220, now)
    osc.frequency.exponentialRampToValueAtTime(isCrit ? 180 : 130, now + 0.07)
    gain.gain.setValueAtTime(vol, now)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08)
    osc.connect(gain); gain.connect(audioCtx.destination)
    osc.start(); osc.stop(now + 0.08)
  }
}

let bgmAudio = null

function stopBgm() {
  if (bgmAudio) {
    bgmAudio.pause()
    bgmAudio = null
  }
}

function playBgm() {
  if (!soundEnabled) return
  stopBgm() // Stop existing
  
  bgmAudio = new Audio('/bgm.mp3')
  bgmAudio.loop = true
  bgmAudio.volume = globalBgmVolume
  bgmAudio.play().catch(e => console.error("BGM blocked by browser", e))
}
