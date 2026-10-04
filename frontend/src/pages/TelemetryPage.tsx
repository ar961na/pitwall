import { useEffect, useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import type { CompareResponse, Driver } from '../api/types'
import { SessionPicker } from '../components/SessionPicker'
import { TrackMap } from '../components/TrackMap'
import { Card, Empty, SeriesLegend, Status, TaskCallout } from '../components/ui'
import { formatLapTime, MISSING, SERIES_DASH } from '../lib/format'
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
  const colorA = byCode[compare?.a ?? a]?.color ?? 'var(--series-2)'
  const rawB = byCode[compare?.b ?? b]?.color ?? 'var(--series-3)'
  const colorB = rawB === colorA ? 'var(--text)' : rawB // teammates share a team colour

  const data = result.data
  const rows = useMemo(() => (data ? toRows(data.channels) : []), [data])

  return (
    <div className="page">
      <section className="controls" aria-label="Lap comparison">
        <div className="toolbar">
          <SessionPicker preferred="Qualifying" onChange={(k) => setSessionKey(k)} />
          <DriverSelect drivers={drivers.data} value={a} onChange={setA} label="Driver A" />
          <span className="muted">vs</span>
          <DriverSelect drivers={drivers.data} value={b} onChange={setB} label="Driver B" />
          <button disabled={!a || !b || a === b || result.loading} onClick={() => setCompare({ a, b })}>
            Compare fastest laps
          </button>
        </div>
        <Status
          loading={drivers.loading}
          error={drivers.error}
          hint="Loading session. The first load of a session takes about 20 s (OpenF1 rate limit)."
        />
        <Status loading={result.loading} error={result.error} hint="Loading telemetry for both laps…" />
      </section>

      {!data && !result.loading && !result.error && (
        <Empty>
          {drivers.data && drivers.data.length === 0
            ? 'No driver data for this session yet. Pick an earlier session.'
            : 'Pick a session and two drivers, then compare their fastest laps.'}
        </Empty>
      )}

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
            <Card title="Speed">
              <SeriesLegend
                items={[
                  { label: data.a.driver, color: colorA },
                  { label: data.b.driver, color: colorB },
                ]}
              />
              <Chart
                names={[data.a.driver, data.b.driver]}
                yLabel="km/h"
                unit=" km/h"
                rows={rows}
                keys={['speed_a', 'speed_b']}
                colors={[colorA, colorB]}
                corners={data.corners}
                height={260}
              />
              <h3>Gap along the lap: above 0 means {data.b.driver} is behind</h3>
              <Chart
                rows={rows}
                keys={['delta']}
                names={[`${data.b.driver} gap`]}
                colors={['var(--text)']}
                yLabel="s"
                unit=" s"
                height={140}
                zeroLine
                xLabel
              />
            </Card>
            <Card title="Faster driver per minisector">
              <SeriesLegend
                items={[
                  { label: `${data.a.driver} faster`, color: colorA },
                  { label: `${data.b.driver} faster`, color: colorB },
                ]}
              />
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

          <Card title="Throttle and brake">
            <SeriesLegend
              items={[
                { label: data.a.driver, color: colorA },
                { label: data.b.driver, color: colorB },
              ]}
            />
            <Chart
              rows={rows}
              keys={['throttle_a', 'throttle_b']}
              names={[data.a.driver, data.b.driver]}
              colors={[colorA, colorB]}
              yLabel="throttle %"
              unit=" %"
              height={140}
            />
            <Chart
              rows={rows}
              keys={['brake_a', 'brake_b']}
              names={[data.a.driver, data.b.driver]}
              colors={[colorA, colorB]}
              yLabel="brake"
              brake
              height={96}
              xLabel
              step
            />
          </Card>

          <Card title="Corner by corner">
            {data.corner_analysis ? (
              <div className="table-wrap">
                <CornerTable rows={data.corner_analysis} a={data.a.driver} b={data.b.driver} />
              </div>
            ) : (
              <TaskCallout task="TASK 1: corner analysis">
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
  names: string[]
  colors: string[]
  height: number
  yLabel: string
  unit?: string
  corners?: CompareResponse['corners']
  zeroLine?: boolean
  xLabel?: boolean
  brake?: boolean
  step?: boolean
}

// Axis lines use the token; tick and axis-title text use --text-muted, which passes 4.5:1.
const AXIS = { stroke: 'var(--chart-axis)', fontSize: 12, tick: { fill: 'var(--text-muted)' } }
const LABEL = { fill: 'var(--text-muted)', fontSize: 12 }

function Chart({
  rows,
  keys,
  names,
  colors,
  height,
  yLabel,
  unit = '',
  corners,
  zeroLine,
  xLabel,
  brake,
  step,
}: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height + (xLabel ? 16 : 0)}>
      {/* syncId links the hover cursor across every chart on the page */}
      <LineChart data={rows} syncId="telemetry" margin={{ top: 8, right: 8, bottom: xLabel ? 16 : 0, left: 8 }}>
        <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
        <XAxis
          dataKey="distance"
          type="number"
          domain={['dataMin', 'dataMax']}
          tickFormatter={(d) => (d / 1000).toFixed(1)}
          label={xLabel ? { value: 'Distance (km)', position: 'insideBottom', offset: -12, ...LABEL } : undefined}
          {...AXIS}
        />
        <YAxis
          domain={brake ? [0, 100] : ['auto', 'auto']}
          ticks={brake ? [0, 100] : undefined}
          tickFormatter={brake ? (v) => (v ? 'on' : 'off') : undefined}
          width={48}
          label={{ value: yLabel, angle: -90, position: 'insideLeft', ...LABEL }}
          {...AXIS}
        />
        <Tooltip
          contentStyle={{ background: 'var(--bg)', border: '1px solid var(--border)' }}
          labelFormatter={(d) => `${Math.round(Number(d))} m`}
          formatter={(v) => (brake ? (Number(v) ? 'on' : 'off') : `${Number(v).toFixed(unit === ' s' ? 3 : 1)}${unit}`)}
        />
        {zeroLine && <ReferenceLine y={0} stroke="var(--text-muted)" />}
        {corners?.map((c) => (
          <ReferenceLine
            key={`${c.number}${c.letter}`}
            x={c.distance}
            stroke="var(--chart-grid)"
            label={{ value: `${c.number}${c.letter}`, position: 'insideTop', fill: 'var(--text-muted)', fontSize: 10 }}
          />
        ))}
        {keys.map((k, i) => (
          <Line
            key={k}
            dataKey={k}
            name={names[i]}
            stroke={colors[i]}
            dot={false}
            strokeWidth={1.5}
            strokeDasharray={SERIES_DASH[i]}
            isAnimationActive={false}
            type={step ? 'stepAfter' : 'linear'}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

function CornerTable({ rows, a, b }: { rows: Record<string, number | null>[]; a: string; b: string }) {
  const f = (v: number | null | undefined, d = 0) => (v == null ? MISSING : v.toFixed(d))
  return (
    <table>
      <thead>
        <tr>
          <th>Turn</th>
          <th>Min speed {a} (km/h)</th>
          <th>Min speed {b} (km/h)</th>
          <th>Brake point {a} (m)</th>
          <th>Brake point {b} (m)</th>
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
