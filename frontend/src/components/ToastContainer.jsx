import React, { useState, useEffect } from 'react'
import { subscribeToast } from '../toastBus'

let nextId = 1
const LIFETIME_MS = 4000

export default function ToastContainer() {
  const [toasts, setToasts] = useState([])

  useEffect(() => {
    return subscribeToast((toast) => {
      const id = nextId++
      setToasts(prev => [...prev, { id, leaving: false, ...toast }])
      setTimeout(() => {
        setToasts(prev => prev.map(t => t.id === id ? { ...t, leaving: true } : t))
        setTimeout(() => {
          setToasts(prev => prev.filter(t => t.id !== id))
        }, 200)
      }, LIFETIME_MS)
    })
  }, [])

  if (toasts.length === 0) return null

  return (
    <div style={{
      position: 'fixed',
      bottom: '1.5rem',
      right: '1.5rem',
      zIndex: 2000,
      display: 'flex',
      flexDirection: 'column',
      gap: '0.5rem',
      alignItems: 'flex-end',
      pointerEvents: 'none',
    }}>
      {toasts.map(t => (
        <div
          key={t.id}
          className={`toast-item ${t.leaving ? 'toast-leaving' : ''}`}
          style={{
            background: '#16161e',
            border: `1px solid ${t.borderColor || 'var(--gold)'}`,
            borderRadius: 6,
            padding: '0.6rem 1rem',
            minWidth: '220px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
          }}
        >
          {t.title && (
            <div style={{ fontFamily: 'Cinzel, serif', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '0.3rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
              {t.title}
            </div>
          )}
          {t.lines.map((line, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: '1.5rem', fontSize: '0.9rem' }}>
              <span style={{ color: 'var(--text-hi)' }}>{line.label}</span>
              <span style={{ color: line.color || 'var(--gold)', fontWeight: 'bold', fontFamily: 'Cinzel, serif' }}>{line.value}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
