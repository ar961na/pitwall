import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api/client'
import type { DegradationResponse } from '../api/types'
import { SessionPicker } from '../components/SessionPicker'
import { Card, CompoundChip, Empty, Status } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { COMPOUND_COLORS, MISSING } from '../lib/format'

const ORDER = ['SOFT', 'MEDIUM', 'HARD']
// A different marker per compound, so the plot does not rely on colour alone.
const SHAPES = { SOFT: 'circle', MEDIUM: 'square', HARD: 'triangle' } as const
const AXIS = { stroke: 'var(--chart-axis)', fontSize: 12, tick: { fill: 'var(--text-muted)' } }
const LABEL = { fill: 'var(--text-muted)', fontSize: 12 }

type Point = DegradationResponse['points'][number]

export function groupByCompound(points: Point[], driver: string): Record<string, Point[]> {
  const out: Record<string, Point[]> = {}
  for (const p of points) {
    if (driver && p.driver !== driver) continue
    ;(out[p.compound] ??= []).push(p)
  }
  return out
}

export function TyresPage() {
  const [sessionKey, setSessionKey] = useState<number | null>(null)
  const [driver, setDriver] = useState('')
  const deg = useApi(sessionKey ? () => api.degradation(sessionKey) : null, [sessionKey])
  const data = deg.data

  const drivers = useMemo(() => [...new Set((data?.points ?? []).map((p) => p.driver))].sort(), [data])
  const byCompound = useMemo(() => groupByCompound(data?.points ?? [], driver), [data, driver])
  const compounds = ORDER.filter((c) => data?.curves[c])

  return (
    <div className="page">
      <section className="controls" aria-label="Tyre degradation">
        <div className="toolbar">
          <SessionPicker
            sessionNames={['Race']}
            onChange={(k) => {
              setSessionKey(k)
              setDriver('')
            }}
          />
          <label>
            Driver
            <select value={driver} onChange={(e) => setDriver(e.target.value)} disabled={!drivers.length}>
              <option value="">All</option>
              {drivers.map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </label>
        </div>
        <Status loading={deg.loading} error={deg.error} hint="Fitting the tyre model for this race…" />
      </section>

      {!data && !deg.loading && !deg.error && <Empty>Pick a race to see how its tyres degraded.</Empty>}

      {data && (
        <div className="grid-2">
          <Card title="Lap time against tyre age">
            <ul className="legend">
              {compounds.map((c) => (
                <li key={c}>
                  <CompoundChip compound={c} />
                </li>
              ))}
              <li className="muted">points: laps, lines: fitted model</li>
            </ul>
            <ResponsiveContainer width="100%" height={380}>
              <ComposedChart margin={{ top: 8, right: 8, bottom: 16, left: 8 }}>
                <CartesianGrid stroke="var(--chart-grid)" />
                <XAxis
                  type="number"
                  dataKey="tyre_life"
                  domain={[0, 'dataMax']}
                  allowDuplicatedCategory={false}
                  label={{ value: 'Tyre age (laps)', position: 'insideBottom', offset: -12, ...LABEL }}
                  {...AXIS}
                />
                <YAxis
                  type="number"
                  dataKey="corrected_s"
                  domain={['auto', 'auto']}
                  width={56}
                  tickFormatter={(v) => Number(v).toFixed(1)}
                  label={{ value: 'Corrected lap time (s)', angle: -90, position: 'insideLeft', ...LABEL }}
                  {...AXIS}
                />
                <Tooltip
                  contentStyle={{ background: 'var(--bg)', border: '1px solid var(--border)' }}
                  formatter={(v, name) => [
                    name === 'tyre_life' ? `${v} laps` : `${Number(v).toFixed(3)} s`,
                    name === 'tyre_life' ? 'Tyre age' : 'Corrected lap time',
                  ]}
                />
                {compounds.map((c) => (
                  <Scatter
                    key={`pts-${c}`}
                    data={byCompound[c] ?? []}
                    fill={COMPOUND_COLORS[c]}
                    fillOpacity={0.45}
                    shape={SHAPES[c as keyof typeof SHAPES]}
                    isAnimationActive={false}
                  />
                ))}
                {compounds.map((c) => (
                  <Line
                    key={`fit-${c}`}
                    data={data.curves[c].tyre_life.map((t, i) => ({
                      tyre_life: t,
                      corrected_s: data.curves[c].corrected_s[i],
                    }))}
                    dataKey="corrected_s"
                    stroke={COMPOUND_COLORS[c]}
                    strokeWidth={2}
                    dot={false}
                    activeDot={false}
                    isAnimationActive={false}
                    tooltipType="none"
                  />
                ))}
                {compounds.map(
                  (c) =>
                    data.cliffs[c] !== undefined && (
                      <ReferenceLine
                        key={`cliff-${c}`}
                        x={data.cliffs[c]}
                        stroke={COMPOUND_COLORS[c]}
                        strokeDasharray="4 4"
                        label={{ value: `${c[0]} cliff`, position: 'insideTopRight', ...LABEL }}
                      />
                    ),
                )}
              </ComposedChart>
            </ResponsiveContainer>
            <p className="muted">
              Lap times are corrected for each driver's pace and for the fuel and track trend (
              {data.model.lap_coef.toFixed(3)} s per lap), so all drivers line up per compound.
            </p>
          </Card>

          <Card title={data.session}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Compound</th>
                    <th>Degradation (s/lap)</th>
                    <th title={`Fresh-tyre pace relative to ${data.model.reference_compound}`}>Offset (s)</th>
                    <th title="Tyre age where at least three stints start losing time faster">Cliff (laps)</th>
                    <th>Laps</th>
                  </tr>
                </thead>
                <tbody>
                  {compounds.map((c) => (
                    <tr key={c}>
                      <td>
                        <CompoundChip compound={c} />
                      </td>
                      <td>{data.model.deg_per_lap[c].toFixed(3)}</td>
                      <td>{data.model.compound_offset[c].toFixed(2)}</td>
                      <td>{data.cliffs[c] ?? MISSING}</td>
                      <td>{data.laps_per_compound[c] ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {compounds.some((c) => data.model.deg_per_lap[c] <= 0) && (
              <p className="error" role="note">
                A compound got faster with age here, which tyres do not do. The track was probably drying or rubbering
                in faster than the model's single trend allows, so do not trust this fit.
              </p>
            )}
            <p className="muted">
              Linear model over {data.model.n_laps} green-flag laps, residual error {data.model.rmse.toFixed(2)} s. With
              one race, fuel burn and track evolution cannot be separated, so compound offsets can absorb part of them.
            </p>
          </Card>
        </div>
      )}
    </div>
  )
}
