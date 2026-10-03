import { useEffect, useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import type { CompareResponse, Driver } from '../api/types'
import { SessionPicker } from '../components/SessionPicker'
import { TrackMap } from '../components/TrackMap'
import { Card, Status, TaskCallout } from '../components/ui'
import { formatLapTime } from '../lib/format'
import { useApi } from '../hooks/useApi'

type Row = Record<string, number>

/** Column-oriented API payload -> array of row objects, which is what recharts wants. */
function toRows(ch: CompareResponse['channels']): Row[] {
  return ch.distance.map((_, i) => {
    const row: Row = {}
    for (const [key, values] of Object.entries(ch)) {
      const v = values[i]
      row[key] = typeof v === 'boolean' ? (v ? 100 : 0) : (v ?? NaN)
    }
    return row
  })
}

export function TelemetryPage() {
  const [sessionKey, setSessionKey] = useState<number | null>(null)
  const [a, setA] = useState('')
  const [b, setB] = useState('')
  const [compare, setCompare] = useState<{ a: string; b: string } | null>(null)

  const drivers = useApi(sessionKey ? () => api.drivers(sessionKey) : null, [sessionKey])
  const result = useApi(compare && sessionKey ? () => api.compare(sessionKey, compare.a, compare.b) : null, [
    sessionKey,
    compare,
  ])

  // Default to P1 vs P2 when a new session's drivers arrive.
  useEffect(() => {
    const list = drivers.data ?? []
    if (list.length >= 2) {
      setA(list[0].code)
      setB(list[1].code)
    }
    setCompare(null)
  }, [drivers.data])

  const byCode = useMemo(
    () => Object.fromEntries((drivers.data ?? []).map((d) => [d.code, d])) as Record<string, Driver>,
    [drivers.data],
  )
  const colorA = byCode[compare?.a ?? a]?.color ?? '#4f9cf9'
  const rawB = byCode[compare?.b ?? b]?.color ?? '#ff8000'
  const colorB = rawB === colorA ? '#f5f5f5' : rawB // teammates share a colour

  const data = result.data
  const rows = useMemo(() => (data ? toRows(data.channels) : []), [data])

  return (
    <div className="page">
      <Card title="Lap comparison">
        <div className="toolbar">
          <SessionPicker preferred="Qualifying" onChange={(k) => setSessionKey(k)} />
          <DriverSelect drivers={drivers.data} value={a} onChange={setA} label="Driver A" />
          <span className="muted">vs</span>
          <DriverSelect drivers={drivers.data} value={b} onChange={setB} label="Driver B" />
          <button disabled={!a || !b || a === b || result.loading} onClick={() => setCompare({ a, b })}>
            Compare fastest laps
          </button>
        </div>
        <Status loading={drivers.loading} error={drivers.error} hint="Loading session (first time can take ~20 s)…" />
        <Status loading={result.loading} error={result.error} hint="Fetching telemetry…" />
      </Card>

      {data && (
        <>
          <div className="stat-row">
            <Stat label={data.a.driver} value={formatLapTime(data.a.lap_time_s)} color={colorA} />
            <Stat label={data.b.driver} value={formatLapTime(data.b.lap_time_s)} color={colorB} />
            <Stat
              label="Gap"
              value={`${data.b.lap_time_s >= data.a.lap_time_s ? '+' : ''}${(data.b.lap_time_s - data.a.lap_time_s).toFixed(3)} s`}
            />
          </div>

          <div className="grid-2">
            <Card title="Speed (km/h)">
              <Chart
                rows={rows}
                keys={['speed_a', 'speed_b']}
                colors={[colorA, colorB]}
                corners={data.corners}
                height={260}
              />
              <h3>Delta (s) · above 0 = {data.b.driver} behind</h3>
              <Chart rows={rows} keys={['delta']} colors={[colorB]} height={140} zeroLine />
            </Card>
            <Card title="Who's faster where">
              <TrackMap
                distance={data.channels.distance as number[]}
                x={data.channels.x_a as number[]}
                y={data.channels.y_a as number[]}
                minisectors={data.minisectors}
                corners={data.corners}
                colorA={colorA}
                colorB={colorB}
              />
            </Card>
          </div>

          <Card title="Throttle & brake (%)">
            <Chart rows={rows} keys={['throttle_a', 'throttle_b']} colors={[colorA, colorB]} height={140} />
            <Chart rows={rows} keys={['brake_a', 'brake_b']} colors={[colorA, colorB]} height={90} step />
          </Card>

          <Card title="Corner by corner">
            {data.corner_analysis ? (
              <CornerTable rows={data.corner_analysis} a={data.a.driver} b={data.b.driver} />
            ) : (
              <TaskCallout task="TASK 1 — corner analysis">
                The backend replied: <code>{data.corner_analysis_status}</code>. Implement{' '}
                <code>corner_analysis()</code> in <code>backend/src/pitwall/telemetry/corners.py</code> and this table
                fills in.
              </TaskCallout>
            )}
          </Card>
        </>
      )}
    </div>
  )
}

function DriverSelect(props: { drivers?: Driver[]; value: string; onChange: (v: string) => void; label: string }) {
  return (
    <select value={props.value} onChange={(e) => props.onChange(e.target.value)} aria-label={props.label}>
      {(props.drivers ?? []).map((d) => (
        <option key={d.code} value={d.code}>
          {d.position ? `P${d.position} ` : ''}
          {d.code} · {d.team}
        </option>
      ))}
    </select>
  )
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="stat" style={color ? { borderTopColor: color } : undefined}>
      <span className="muted">{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

interface ChartProps {
  rows: Row[]
  keys: string[]
  colors: string[]
  height: number
  corners?: CompareResponse['corners']
  zeroLine?: boolean
  step?: boolean
}

function Chart({ rows, keys, colors, height, corners, zeroLine, step }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      {/* syncId links the hover cursor across every chart on the page */}
      <LineChart data={rows} syncId="telemetry" margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        <XAxis
          dataKey="distance"
          type="number"
          domain={['dataMin', 'dataMax']}
          tickFormatter={(d) => `${(d / 1000).toFixed(1)}k`}
          stroke="var(--muted)"
          fontSize={11}
        />
        <YAxis stroke="var(--muted)" fontSize={11} domain={['auto', 'auto']} />
        <Tooltip
          contentStyle={{ background: 'var(--panel)', border: '1px solid var(--border)' }}
          labelFormatter={(d) => `${Math.round(Number(d))} m`}
          formatter={(v) => Number(v).toFixed(2)}
        />
        {zeroLine && <ReferenceLine y={0} stroke="var(--muted)" />}
        {corners?.map((c) => (
          <ReferenceLine
            key={`${c.number}${c.letter}`}
            x={c.distance}
            stroke="var(--grid)"
            label={{ value: `${c.number}${c.letter}`, position: 'insideTop', fill: 'var(--muted)', fontSize: 10 }}
          />
        ))}
        {keys.map((k, i) => (
          <Line
            key={k}
            dataKey={k}
            stroke={colors[i]}
            dot={false}
            strokeWidth={1.5}
            strokeDasharray={i === 1 ? '5 3' : undefined}
            isAnimationActive={false}
            type={step ? 'stepAfter' : 'linear'}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

function CornerTable({ rows, a, b }: { rows: Record<string, number | null>[]; a: string; b: string }) {
  const f = (v: number | null | undefined, d = 0) => (v == null ? '—' : v.toFixed(d))
  return (
    <table>
      <thead>
        <tr>
          <th>Turn</th>
          <th>Min speed {a}</th>
          <th>Min speed {b}</th>
          <th>Brake point {a}</th>
          <th>Brake point {b}</th>
          <th>{b} gains (s)</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.corner}>
            <td>{r.corner}</td>
            <td>{f(r.min_speed_a)}</td>
            <td>{f(r.min_speed_b)}</td>
            <td>{f(r.brake_point_a)}</td>
            <td>{f(r.brake_point_b)}</td>
            <td className={(r.time_gain_b_s ?? 0) > 0 ? 'good' : 'bad'}>{f(r.time_gain_b_s, 3)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
