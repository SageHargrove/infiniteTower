// Tiny module-level event bus so the API client (a plain module, not a React
// component) can fire reward toasts without needing hook/context access.
const listeners = new Set()

export function subscribeToast(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function emitToast(toast) {
  listeners.forEach(fn => fn(toast))
}
