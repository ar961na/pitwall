import type { ReactNode } from 'react'
import { COMPOUND_COLORS } from '../lib/format'

export function Card({ title, children, actions }: { title?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="card">
      {(title || actions) && (
        <header className="card-header">
          {title && <h2>{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  )
}

export function Status({ loading, error, hint }: { loading?: boolean; error?: string; hint?: string }) {
  if (error) return <p className="error">⚠ {error}</p>
  if (loading) return <p className="muted">⏳ {hint ?? 'Loading…'}</p>
  return null
}

/** Marks a part of the app that's waiting for one of the hands-on tasks. */
export function TaskCallout({ task, children }: { task: string; children: ReactNode }) {
  return (
    <div className="task-callout">
      <strong>🛠 {task}</strong>
      <div>{children}</div>
    </div>
  )
}

export function CompoundChip({ compound, laps }: { compound: string; laps?: number }) {
  return (
    <span className="chip" style={{ borderColor: COMPOUND_COLORS[compound] ?? '#888' }}>
      <span className="dot" style={{ background: COMPOUND_COLORS[compound] ?? '#888' }} />
      {compound[0]}
      {laps !== undefined && <small>{laps}</small>}
    </span>
  )
}
