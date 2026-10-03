import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { EventInfo } from '../api/types'
import { useApi } from '../hooks/useApi'

const FIRST_YEAR = 2023 // OpenF1 coverage starts in 2023
const THIS_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: THIS_YEAR - FIRST_YEAR + 1 }, (_, i) => THIS_YEAR - i)

interface Props {
  /** Only offer these session types, e.g. ["Race"]. Omit for all. */
  sessionNames?: string[]
  /** Pre-select this session type when switching events. */
  preferred?: string
  onChange: (sessionKey: number | null, label: string) => void
}

export function SessionPicker({ sessionNames, preferred, onChange }: Props) {
  const [year, setYear] = useState(THIS_YEAR)
  const [meetingKey, setMeetingKey] = useState<number | null>(null)
  const [sessionKey, setSessionKey] = useState<number | null>(null)
  const events = useApi(() => api.events(year), [year])

  // Only weekends with at least one finished session of an allowed type.
  const allowed = (name: string) => !sessionNames || sessionNames.includes(name)
  const usable: EventInfo[] = (events.data ?? []).filter((e) => e.sessions.some((s) => s.completed && allowed(s.name)))
  const event = usable.find((e) => e.meeting_key === meetingKey)
  const sessions = event?.sessions.filter((s) => s.completed && allowed(s.name)) ?? []

  // Default to the most recent weekend when the year's events arrive.
  useEffect(() => {
    if (usable.length && !usable.some((e) => e.meeting_key === meetingKey)) {
      setMeetingKey(usable[usable.length - 1].meeting_key)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events.data])

  // Pick a session when the weekend changes.
  useEffect(() => {
    if (!event) return
    const pick = sessions.find((s) => s.name === preferred) ?? sessions[sessions.length - 1]
    setSessionKey(pick?.session_key ?? null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meetingKey, event?.meeting_key])

  // Tell the parent whenever the chosen session changes.
  useEffect(() => {
    const s = sessions.find((x) => x.session_key === sessionKey)
    onChange(sessionKey, s && event ? `${year} ${event.name} · ${s.name}` : '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionKey])

  return (
    <div className="picker">
      <select value={year} onChange={(e) => setYear(Number(e.target.value))} aria-label="Season">
        {YEARS.map((y) => (
          <option key={y}>{y}</option>
        ))}
      </select>
      <select
        value={meetingKey ?? ''}
        onChange={(e) => setMeetingKey(Number(e.target.value))}
        disabled={events.loading || !usable.length}
        aria-label="Grand Prix"
      >
        {events.loading && <option>Loading calendar…</option>}
        {usable.map((e) => (
          <option key={e.meeting_key} value={e.meeting_key}>
            R{e.round} · {e.name} ({e.circuit})
          </option>
        ))}
      </select>
      <select
        value={sessionKey ?? ''}
        onChange={(e) => setSessionKey(Number(e.target.value))}
        disabled={!sessions.length}
        aria-label="Session"
      >
        {sessions.map((s) => (
          <option key={s.session_key} value={s.session_key}>
            {s.name}
          </option>
        ))}
      </select>
      {events.error && <span className="error">{events.error}</span>}
    </div>
  )
}
