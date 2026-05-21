import { useEffect } from 'react'

export default function SuccessBanner({ message, onDismiss, timeoutMs = 3500 }) {
  useEffect(() => {
    if (!message || !onDismiss) return
    const id = setTimeout(onDismiss, timeoutMs)
    return () => clearTimeout(id)
  }, [message, onDismiss, timeoutMs])

  if (!message) return null

  return (
    <div
      role="status"
      className="flex items-center justify-between gap-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
    >
      <span>{message}</span>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="text-emerald-700 hover:text-emerald-900"
        >
          ×
        </button>
      )}
    </div>
  )
}
