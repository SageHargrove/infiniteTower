import React from 'react'

// Shared visual shell for a fairy popup tip — FairyGuide.jsx (tower-floor
// triggers) and any other page wanting a one-off fairy tip both render
// through this so the look stays consistent without duplicating the JSX.
export default function FairyTip({ show, message, fairyGender, onDismiss }) {
  if (!show) return null

  const fairyImg = `http://localhost:8000/static/portraits/fairy/${fairyGender === 'male' ? 'male' : 'female'}.png`

  return (
    <div style={{
      position: 'fixed',
      bottom: '30px',
      right: '30px',
      width: '320px',
      background: 'rgba(15, 20, 25, 0.95)',
      border: '2px solid #a88be0',
      borderRadius: '8px',
      padding: '1rem',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '0 8px 32px rgba(168, 139, 224, 0.2)',
      zIndex: 9999,
      animation: 'slideIn 0.3s ease-out'
    }}>
      <style>{`
        @keyframes slideIn {
          from { transform: translateX(120%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          overflow: 'hidden',
          border: '1px solid #a88be0',
          background: '#222'
        }}>
          <img src={fairyImg} style={{width: '100%', height: '100%', objectFit: 'cover'}} onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }} />
          <div style={{ width: '100%', height: '100%', display: 'none', alignItems: 'center', justifyContent: 'center', fontSize: '2rem' }}>
            🧚
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: 'Cinzel, serif', color: '#a88be0', fontWeight: 'bold', marginBottom: '0.4rem', fontSize: '1.1rem' }}>
            Fairy Guide
          </div>
          <div style={{ fontSize: '0.9rem', lineHeight: '1.4', color: '#e0e0e0' }}>
            {message}
          </div>
        </div>
      </div>

      <button
        onClick={onDismiss}
        style={{
          position: 'absolute',
          top: '5px',
          right: '5px',
          background: 'none',
          border: 'none',
          color: '#888',
          cursor: 'pointer',
          fontSize: '1.2rem'
        }}
      >
        ×
      </button>
    </div>
  )
}
