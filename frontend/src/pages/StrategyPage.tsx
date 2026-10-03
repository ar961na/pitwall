import { useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import type { CompoundParams, OptimizeResponse, RaceParams } from '../api/types'
import { SessionPicker } from '../components/SessionPicker'
import { Card, CompoundChip, Status } from '../components/ui'
import { useApi } from '../hooks/useApi'

const TRACE_COLORS = ['#e10600', '#4f9cf9', '#a3a3a3']

// [field, label, step] for the scalar race parameters shown in the form
const RACE_FIELDS: [keyof RaceParams, string, number][] = [
  ['total_laps', 'Race laps', 1],
  ['base_lap_time_s', 'Base lap (s)', 0.1],
  ['lap_coef_s', 'Fuel/track (s per lap)', 0.005],
  ['pit_loss_s', 'Pit loss (s)', 0.5],
  ['sc_prob_per_lap', 'SC chance per lap', 0.005],
  ['sc_pit_loss_factor', 'Pit loss under SC (×)', 0.05],
  ['lap_noise_s', 'Lap noise σ (s)', 0.05],
]
const COMPOUND_FIELDS: [keyof CompoundParams, string, number][] = [
  ['offset_s', 'Offset (s)', 0.05],
  ['deg_s_per_lap', 'Deg (s/lap)', 0.005],
  ['cliff_age', 'Cliff (lap)', 1],
  ['cliff_s_per_lap2', 'Cliff rate', 0.005],
]

export function StrategyPage() {
  const defaults = useApi(() => api.strategyDefaults(), [])
  const [edited, setEdited] = useState<RaceParams | null>(null)
  const params = edited ?? defaults.data ?? null

  const [raceKey, setRaceKey] = useState<number | null>(null)
  const [raceLabel, setRaceLabel] = useState('')
  const [calibrating, setCalibrating] = useState(false)
  const [maxStops, setMaxStops] = useState(2)
  const [nSims, setNSims] = useState(2000)
  const [result, setResult] = useState<OptimizeResponse | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string>()

  // Event handlers that call the API directly (instead of useApi) because they run on click.
  async function calibrate() {
    if (!raceKey) return
    setCalibrating(true)
    setError(undefined)
    try {
      setEdited(await api.calibrate(raceKey))
      setResult(null)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setCalibrating(false)
    }
  }

  async function run() {
    if (!params) return
    setRunning(true)
    setError(undefined)
    try {
      setResult(await api.optimize({ params, max_stops: maxStops, min_stint: 8, n_sims: nSims, seed: 0 }))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setRunning(false)
    }
  }

  const setField = (key: keyof RaceParams, value: number) => params && setEdited({ ...params, [key]: value })
  const setCompound = (name: string, key: keyof CompoundParams, value: number) =>
    params &&
    setEdited({ ...params, compounds: { ...params.compounds, [name]: { ...params.compounds[name], [key]: value } } })

  return (
    <div className="page">
      <Card title="Calibrate from a real race (optional)">
        <div className="toolbar">
          <SessionPicker
            sessionNames={['Race']}
            onChange={(k, label) => {
              setRaceKey(k)
              setRaceLabel(label)
            }}
          />
          <button onClick={calibrate} disabled={!raceKey || calibrating}>
            {calibrating ? 'Fitting tyre model…' : 'Fit tyres + pit loss'}
          </button>
          {edited && (
            <button className="secondary" onClick={() => setEdited(null)}>
              Reset to defaults
            </button>
          )}
        </div>
        <p className="muted">
          Fits the linear degradation model on {raceLabel || 'the selected race'}'s green-flag laps and takes the
          circuit's pit loss. Cliffs still come from defaults until TASK 2.
        </p>
      </Card>

      <Status loading={defaults.loading} error={defaults.error ?? error} />

      {params && (
        <div className="grid-2">
          <Card title="Race">
            <div className="form-grid">
              {RACE_FIELDS.map(([key, label, step]) => (
                <label key={key}>
                  {label}
                  <input
                    type="number"
                    step={step}
                    value={Number((params[key] as number).toFixed(4))}
                    onChange={(e) => setField(key, Number(e.target.value))}
                  />
                </label>
              ))}
            </div>
          </Card>
          <Card title="Tyres">
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th />
                    {COMPOUND_FIELDS.map(([, label]) => (
                      <th key={label}>{label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(params.compounds).map(([name, c]) => (
                    <tr key={name}>
                      <td>
                        <CompoundChip compound={name} />
                      </td>
                      {COMPOUND_FIELDS.map(([key, , step]) => (
                        <td key={key}>
                          <input
                            type="number"
                            step={step}
                            value={Number(c[key].toFixed(4))}
                            onChange={(e) => setCompound(name, key, Number(e.target.value))}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      <Card title="Optimise">
        <div className="toolbar">
          <label>
            Max stops{' '}
            <select value={maxStops} onChange={(e) => setMaxStops(Number(e.target.value))}>
              <option>1</option>
              <option>2</option>
              <option>3</option>
            </select>
          </label>
          <label>
            Simulations{' '}
            <select value={nSims} onChange={(e) => setNSims(Number(e.target.value))}>
              {[500, 2000, 5000, 10000].map((n) => (
                <option key={n}>{n}</option>
              ))}
            </select>
          </label>
          <button onClick={run} disabled={!params || running}>
            {running ? 'Simulating…' : 'Find best strategy'}
          </button>
        </div>
      </Card>

      {result && <Results result={result} />}
    </div>
  )
}

function Results({ result }: { result: OptimizeResponse }) {
  const top = result.results.slice(0, 3)
  const laps = top[0].clean_lap_times_s ?? []
  const rows = laps.map((_, i) => {
    const row: Record<string, number> = { lap: i + 1 }
    top.forEach((r) => (row[r.label] = r.clean_lap_times_s![i]))
    return row
  })

  return (
    <>
      <Card title="Ranked strategies (mean race time over simulated races)">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Strategy</th>
                <th>Pit laps</th>
                <th>Gap (s)</th>
                <th title="Spread of race time across simulations, relative to the best mean. Safety cars cause the long tail.">
                  P10 – P90 vs best (s)
                </th>
                <th title="Share of simulated races where this strategy was the fastest">P(best)</th>
              </tr>
            </thead>
            <tbody>
              {result.results.slice(0, 12).map((r, i) => (
                <tr key={r.label}>
                  <td>{i + 1}</td>
                  <td>
                    {r.stints.map((s, k) => (
                      <CompoundChip key={k} compound={s.compound} laps={s.laps} />
                    ))}
                  </td>
                  <td>{r.pit_laps.join(', ')}</td>
                  <td>{i === 0 ? '—' : `+${r.gap_s.toFixed(2)}`}</td>
                  <td className="muted">
                    {(r.p10_s - result.results[0].mean_s).toFixed(1)} …{' '}
                    {(r.p90_s - result.results[0].mean_s).toFixed(1)}
                  </td>
                  <td>
                    <div className="bar">
                      <div style={{ width: `${r.p_best * 100}%` }} />
                      <span>{(r.p_best * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card title="Lap times of the top 3 (green-flag, no noise)">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="lap" stroke="var(--muted)" fontSize={11} />
            <YAxis domain={['auto', 'auto']} stroke="var(--muted)" fontSize={11} />
            <Tooltip
              contentStyle={{ background: 'var(--panel)', border: '1px solid var(--border)' }}
              formatter={(v) => Number(v).toFixed(3)}
            />
            <Legend />
            {top.map((r, k) => (
              <Line
                key={r.label}
                dataKey={r.label}
                stroke={TRACE_COLORS[k]}
                dot={false}
                isAnimationActive={false}
                strokeWidth={k === 0 ? 2 : 1.2}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
        <p className="muted">
          Pit stops show up as drops back to fresh-tyre pace; slope = degradation minus fuel burn.
        </p>
      </Card>
    </>
  )
}
