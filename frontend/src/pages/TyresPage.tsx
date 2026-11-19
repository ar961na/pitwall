import { useMemo, useState } from 'react'
import {
  Area,
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
import type { DegradationResponse, PaceModelResponse, StintForecastResponse } from '../api/types'
import { SessionPicker } from '../components/SessionPicker'
import { Card, CompoundChip, Empty, SeriesLegend, Status } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { COMPOUND_COLORS, MISSING, SERIES_DASH } from '../lib/format'

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
  const pace = useApi(sessionKey ? () => api.paceModel(sessionKey) : null, [sessionKey])
  const forecast = useApi(sessionKey && driver ? () => api.stintForecast(sessionKey, driver) : null, [
    sessionKey,
    driver,
  ])
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

      {data && driver && (
        <StintForecastCard forecast={forecast.data} loading={forecast.loading} error={forecast.error} />
      )}
      {data && <PaceModelCard pace={pace.data} loading={pace.loading} error={pace.error} />}
    </div>
  )
}

export function bandRows(curve: PaceModelResponse['curves'][string]) {
  // recharts draws a band from a [low, high] pair in one data key
  return curve.tyre_life.map((t, i) => ({
    tyre_life: t,
    band: [curve.lo[i], curve.hi[i]] as [number, number],
    median: curve.median[i],
  }))
}

function PaceModelCard({ pace, loading, error }: { pace?: PaceModelResponse; loading: boolean; error?: string }) {
  if (loading) return <Status loading hint="Loading the multi-race pace model…" />
  if (!pace)
    return (
      <Card title="Expected pace across all races">
        <Empty>
          {error?.includes('train')
            ? 'No multi-race pace model is trained on this server (make train-pace).'
            : 'The multi-race pace model is not available here.'}
        </Empty>
      </Card>
    )
  const m = pace.metrics
  const compounds = ORDER.filter((c) => pace.curves[c])
  return (
    <Card title="Expected pace across all races">
      <div className="grid-2">
        <div>
          {compounds.map((c) => (
            <div key={c}>
              <h3>
                <CompoundChip compound={c} />
              </h3>
              <ResponsiveContainer width="100%" height={160}>
                <ComposedChart data={bandRows(pace.curves[c])} margin={{ top: 8, right: 8, bottom: 16, left: 8 }}>
                  <CartesianGrid stroke="var(--chart-grid)" />
                  <XAxis
                    dataKey="tyre_life"
                    type="number"
                    domain={[1, 'dataMax']}
                    label={{ value: 'Tyre age (laps)', position: 'insideBottom', offset: -12, ...LABEL }}
                    {...AXIS}
                  />
                  <YAxis
                    domain={['auto', 'auto']}
                    width={56}
                    tickFormatter={(v) => Number(v).toFixed(1)}
                    label={{ value: 'vs median (s)', angle: -90, position: 'insideLeft', ...LABEL }}
                    {...AXIS}
                  />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg)', border: '1px solid var(--border)' }}
                    labelFormatter={(t) => `Tyre age ${t} laps`}
                    formatter={(v, name) =>
                      Array.isArray(v)
                        ? [`${Number(v[0]).toFixed(2)} to ${Number(v[1]).toFixed(2)} s`, '80% range']
                        : [`${Number(v).toFixed(2)} s`, name === 'median' ? 'Expected' : String(name)]
                    }
                  />
                  <Area
                    dataKey="band"
                    stroke="none"
                    fill={COMPOUND_COLORS[c]}
                    fillOpacity={0.2}
                    isAnimationActive={false}
                  />
                  <Line
                    dataKey="median"
                    stroke={COMPOUND_COLORS[c]}
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
        <div>
          <p>
            A LightGBM model trained on {Number(m.n_laps).toLocaleString('en')} laps from {m.n_races} races predicts a
            lap against the driver's median for the race, at half distance on {pace.circuit}. The shaded range should
            hold 80% of laps.
          </p>
          {!pace.circuit_in_training && (
            <p className="error" role="note">
              This circuit was not in the training races, so the curves use the model's average circuit.
            </p>
          )}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>On held-out later races</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Mean error, this model</td>
                  <td>{Number(m.mae_gbm_s).toFixed(3)} s</td>
                </tr>
                <tr>
                  <td>Mean error, pooled linear model</td>
                  <td>{Number(m.mae_linear_s).toFixed(3)} s</td>
                </tr>
                <tr>
                  <td>Laps inside the 80% range</td>
                  <td>{(Number(m.coverage_80_conformal) * 100).toFixed(1)}%</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="muted">
            The y-axis differs from the chart above: this one is relative to each driver's median lap, not corrected for
            fuel.
          </p>
        </div>
      </div>
    </Card>
  )
}

type GapRow = { lap: number; actual: number | null; gru: number | null; persistence: number | null }

/** Insert an empty row wherever laps are not consecutive, so lines break at stops and gaps. */
export function withGaps(laps: StintForecastResponse['laps']): GapRow[] {
  const out: GapRow[] = []
  laps.forEach((l, i) => {
    if (i > 0 && l.lap - laps[i - 1].lap > 1) out.push({ lap: l.lap - 0.5, actual: null, gru: null, persistence: null })
    out.push({ lap: l.lap, actual: l.actual, gru: l.gru, persistence: l.persistence })
  })
  return out
}

function StintForecastCard({
  forecast,
  loading,
  error,
}: {
  forecast?: StintForecastResponse
  loading: boolean
  error?: string
}) {
  if (loading) return <Status loading hint="Running the stint forecaster…" />
  if (!forecast)
    return (
      <Card title="Next-lap forecast">
        <Empty>
          {error?.includes('stint forecaster')
            ? 'The stint forecaster is not available on this server (it needs PyTorch and make train-stint).'
            : (error ?? 'No forecast for this driver.')}
        </Empty>
      </Card>
    )
  const m = forecast.model
  const fmt = (v: number | null) => (v === null ? MISSING : `${v.toFixed(3)} s`)
  return (
    <Card title={`Next-lap forecast for ${forecast.driver}`}>
      <SeriesLegend
        items={[
          { label: 'Actual', color: 'var(--text)' },
          { label: 'GRU forecast', color: 'var(--series-1)' },
          { label: 'Repeat last lap', color: 'var(--series-2)' },
        ]}
      />
      {forecast.laps.length ? (
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={withGaps(forecast.laps)} margin={{ top: 8, right: 8, bottom: 16, left: 8 }}>
            <CartesianGrid stroke="var(--chart-grid)" />
            <XAxis
              dataKey="lap"
              type="number"
              domain={['dataMin', 'dataMax']}
              label={{ value: 'Lap', position: 'insideBottom', offset: -12, ...LABEL }}
              {...AXIS}
            />
            <YAxis
              domain={['auto', 'auto']}
              width={56}
              tickFormatter={(v) => Number(v).toFixed(1)}
              label={{ value: 'vs median (s)', angle: -90, position: 'insideLeft', ...LABEL }}
              {...AXIS}
            />
            <Tooltip
              contentStyle={{ background: 'var(--bg)', border: '1px solid var(--border)' }}
              labelFormatter={(lap) => `Lap ${lap}`}
              formatter={(v, name) => [`${Number(v).toFixed(3)} s`, String(name)]}
            />
            {(
              [
                ['actual', 'Actual', 'var(--text)'],
                ['gru', 'GRU forecast', 'var(--series-1)'],
                ['persistence', 'Repeat last lap', 'var(--series-2)'],
              ] as const
            ).map(([key, name, color], i) => (
              <Line
                key={key}
                dataKey={key}
                name={name}
                stroke={color}
                strokeDasharray={SERIES_DASH[i]}
                strokeWidth={i === 0 ? 2 : 1.5}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      ) : (
        <Empty>No stint of this driver has the 9 consecutive green-flag laps a forecast needs.</Empty>
      )}
      <p>
        Mean error on this driver's laps: GRU {fmt(forecast.mae.gru)}, repeating the last lap{' '}
        {fmt(forecast.mae.persistence)}.
        {forecast.in_training_data && ' This race was in the training data, so this is not a fair test.'}
      </p>
      <p className="muted">
        A GRU reads the previous 8 laps of a stint and predicts the next one. Across all held-out races it is 13% more
        accurate than repeating the last lap ({Number(m.mae_gru_s).toFixed(3)} s vs{' '}
        {Number(m.mae_persistence_s).toFixed(3)} s); on a single driver the two are often close. Laps after a pit stop,
        safety car or outlier start a new stretch, so gaps in the line are expected.
      </p>
    </Card>
  )
}
