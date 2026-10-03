import { useState } from 'react'
import { SessionPicker } from '../components/SessionPicker'
import { Card, TaskCallout } from '../components/ui'

/**
 * FRONTEND TASK R1 — docs/tasks/R1-tyres-page.md
 *
 * The backend already serves everything this page needs:
 *   GET /api/sessions/{session_key}/degradation   ->  DegradationResponse (see api/types.ts)
 *
 * Build:
 *   1. fetch it with useApi + api.degradation (copy the pattern from TelemetryPage)
 *   2. a scatter of tyre_life (x) vs corrected_s (y), one colour per compound (COMPOUND_COLORS)
 *   3. the fitted line per compound on top (curves[compound])
 *   4. a small table: compound | deg s/lap | offset vs reference | n laps
 */
export function TyresPage() {
  const [sessionKey, setSessionKey] = useState<number | null>(null)

  return (
    <div className="page">
      <Card title="Tyre degradation">
        <SessionPicker sessionNames={['Race']} onChange={(k) => setSessionKey(k)} />
      </Card>
      <TaskCallout task="TASK R1 — build this page">
        Selected session_key: <code>{sessionKey ?? '—'}</code>. Fetch{' '}
        <code>/api/sessions/{sessionKey ?? '{key}'}/degradation</code> and plot it. Instructions in{' '}
        <code>docs/tasks/R1-tyres-page.md</code>.
      </TaskCallout>
    </div>
  )
}
