import type { ReactNode } from 'react'
import { COMPOUND_COLORS, SERIES_DASH } from '../lib/format'

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
  if (error)
    return (
      <p className="error" role="alert">
        Error: {error}
      </p>
    )
  if (loading)
    return (
      <p className="muted" role="status">
        {hint ?? 'Loading…'}
      </p>
    )
  return null
}

/** What the user sees before there is anything to show. */
export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>
}

/** Marks a part of the app that's waiting for one of the hands-on tasks. */
export function TaskCallout({ task, children }: { task: string; children: ReactNode }) {
  return (
    <div className="task-callout">
      <strong>{task}</strong>
      <div>{children}</div>
    </div>
  )
}

export function CompoundChip({ compound, laps }: { compound: string; laps?: number }) {
  return (
    <span className="chip" title={laps === undefined ? compound : `${compound}, ${laps} laps`}>
      <span className="dot" style={{ background: COMPOUND_COLORS[compound] ?? 'var(--text-muted)' }} />
      {compound[0]}
      {laps !== undefined && <small>{laps}</small>}
    </span>
  )
}

/** Legend entries drawn with the same colour and dash as the chart lines. */
export function SeriesLegend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <ul className="legend">
      {items.map((it, i) => (
        <li key={it.label}>
          <svg width="28" height="8" aria-hidden="true">
            <line x1="0" y1="4" x2="28" y2="4" stroke={it.color} strokeWidth="2" strokeDasharray={SERIES_DASH[i]} />
          </svg>
          {it.label}
        </li>
      ))}
    </ul>
  )
}
