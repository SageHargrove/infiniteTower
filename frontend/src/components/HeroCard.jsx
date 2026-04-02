import React from 'react'

const MORALE_STATE_LABEL = {
  steady: 'Steady', shaken: 'Shaken', fearful: 'Fearful', broken: 'Broken',
}

const CLASS_COLORS = {
  'Warrior': '#c87830',
  'Spearman': '#c8a030',
  'Thief': '#7030c8',
  'Archer': '#30a030',
  'Mage': '#4060c8',
  'Magic Engineer': '#30b8c8',
  'Chef': '#c85030',
  'Medic': '#30c870',
  'Scout': '#a8c830',
  'Blacksmith': '#888',
  'Quartermaster': '#c8c030',
  'Tactician': '#8030c8',
  'Priest': '#c0c0e0',
  'Alchemist': '#30c8a0',
  'Classless': '#555',
}

const CLASS_ICONS = {
  'Warrior': '⚔', 'Spearman': '🗡', 'Thief': '🗝', 'Archer': '🏹',
  'Mage': '✦', 'Magic Engineer': '⚙', 'Chef': '🍖', 'Medic': '✚',
  'Scout': '👁', 'Blacksmith': '🔨', 'Quartermaster': '💰',
  'Tactician': '♟', 'Priest': '☽', 'Alchemist': '⚗', 'Classless': '—',
}

export function Stars({ count, max = 7 }) {
  return (
    <div className={`stars birth-star-${count}`}>
      {Array.from({ length: max }).map((_, i) => (
        <span key={i} className="star">{i < count ? '★' : '☆'}</span>
      ))}
    </div>
  )
}

export function ClassBadge({ heroClass }) {
  if (!heroClass) return null
  const color = CLASS_COLORS[heroClass] || '#555'
  const icon = CLASS_ICONS[heroClass] || '?'
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '3px',
      background: `${color}22`, border: `1px solid ${color}66`,
      color: color, borderRadius: 3,
      padding: '1px 6px', fontSize: '0.7rem',
      fontFamily: 'Cinzel, serif', letterSpacing: '0.05em',
      marginTop: '0.3rem',
    }}>
      {icon} {heroClass}
    </span>
  )
}

export function LevelBadge({ level, ascensionStar }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      background: 'rgba(201,168,76,0.1)', border: '1px solid rgba(201,168,76,0.3)',
      color: 'var(--gold)', borderRadius: 3,
      padding: '1px 6px', fontSize: '0.7rem',
      fontFamily: 'Cinzel, serif', marginLeft: '0.3rem',
    }}>
      Lv.{level}
    </span>
  )
}

export function MoraleBar({ morale, state }) {
  return (
    <div className="morale-bar-wrap">
      <div className="morale-label">
        <span>Morale</span>
        <span className={`text-${state === 'steady' ? 'green' : state === 'broken' ? 'red' : 'gold'}`}>
          {MORALE_STATE_LABEL[state] || state} ({morale})
        </span>
      </div>
      <div className="morale-bar-bg">
        <div className={`morale-bar-fill ${state}`} style={{ width: `${morale}%` }} />
      </div>
    </div>
  )
}

export function HpBar({ hp, maxHp }) {
  const pct = Math.max(0, Math.min(100, (hp / maxHp) * 100))
  return (
    <div className="hp-bar-wrap">
      <div className="morale-label">
        <span>HP</span>
        <span>{hp} / {maxHp}</span>
      </div>
      <div className="hp-bar-bg">
        <div className="hp-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function HeroCard({ hero, selected, onClick, showFull = false }) {
  if (!hero) return null
  const dead = !hero.is_alive

  return (
    <div
      className={`hero-card ${selected ? 'selected' : ''} ${dead ? 'dead' : ''}`}
      onClick={!dead && onClick ? onClick : undefined}
    >
      {hero.portrait_path && (
        <img
          src={`http://localhost:8000/${hero.portrait_path}`}
          alt={hero.name}
          style={{ width: '100%', height: 140, objectFit: 'cover', objectPosition: 'top', borderRadius: 2, marginBottom: '0.5rem' }}
        />
      )}

      <div className="hero-name">{hero.name}</div>
      <div className="hero-title">{hero.title}</div>

      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.3rem', marginTop: '0.3rem' }}>
        <Stars count={hero.birth_star} />
        <LevelBadge level={hero.level || 1} ascensionStar={hero.ascension_star || 0} />
      </div>

      <ClassBadge heroClass={hero.hero_class} />

      {dead && <div className="text-red text-sm" style={{ marginTop: '0.3rem' }}>✦ Fallen</div>}

      {!dead && (
        <>
          <HpBar hp={hero.hp} maxHp={hero.max_hp} />
          <MoraleBar morale={hero.morale} state={hero.morale_state || 'steady'} />

          <div className="stats-row">
            <div className="stat">ATK <span>{hero.attack}</span></div>
            <div className="stat">DEF <span>{hero.defense}</span></div>
            <div className="stat">SPD <span>{hero.speed}</span></div>
          </div>

          {showFull && (
            <div style={{ marginTop: '0.75rem', borderTop: '1px solid var(--border)', paddingTop: '0.75rem' }}>
              <div className="text-sm text-dim" style={{ fontStyle: 'italic', lineHeight: 1.6 }}>
                {hero.backstory}
              </div>
              <div className="text-sm text-dim" style={{ marginTop: '0.4rem', lineHeight: 1.5 }}>
                {hero.personality}
              </div>
              <div className="stats-row" style={{ marginTop: '0.5rem' }}>
                <div className="stat">Kills <span>{hero.kills}</span></div>
                <div className="stat">Floors <span>{hero.floors_survived}</span></div>
                <div className="stat">Stress <span>{hero.stress}</span></div>
                <div className="stat">Trauma <span>{hero.trauma}</span></div>
              </div>
              {hero.can_pilot === 1 && (
                <div style={{ marginTop: '0.4rem', color: 'var(--blue)', fontSize: '0.75rem' }}>
                  ⚙ Can pilot vessels
                </div>
              )}
            </div>
          )}
        </>
      )}

      {selected && (
        <div style={{
          position: 'absolute', top: 6, right: 8,
          color: 'var(--gold)', fontSize: '0.7rem', fontFamily: 'Cinzel, serif'
        }}>TEAM</div>
      )}
    </div>
  )
}