import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Prediction, PredictRound } from '../api/types'
import { STATIC_DEMO } from '../api/static'
import { Card, Empty, Status } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { MISSING } from '../lib/format'

const FIRST_YEAR = 2014 // the model's first training season
const THIS_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: THIS_YEAR - FIRST_YEAR + 1 }, (_, i) => THIS_YEAR - i)

const STATE_TEXT = {
  finished: 'Race finished: the forecast is shown next to the result.',
  qualified: 'Qualifying is done: forecast from the grid, qualifying pace and form.',
  upcoming: 'Before qualifying: forecast from form and history only, so it is less accurate.',
} as const

/** The round to show first: the next race if there is one, otherwise the latest. */
export function defaultRound(rounds: PredictRound[]): number | null {
  if (!rounds.length) return null
  return (rounds.find((r) => r.state !== 'finished') ?? rounds[rounds.length - 1]).round
}

const pct = (p: number) => (p < 0.005 ? '<1%' : `${Math.round(p * 100)}%`)

export function PredictPage() {
  const [year, setYear] = useState(THIS_YEAR)
  const [round, setRound] = useState<number | null>(null)
  const rounds = useApi(() => api.predictRounds(year), [year])
  const forecast = useApi(round ? () => api.predict(year, round) : null, [year, round])

  useEffect(() => {
    setRound(defaultRound(rounds.data ?? []))
  }, [rounds.data])

  const data = forecast.data
  return (
    <div className="page">
      <section className="controls" aria-label="Race prediction">
        <div className="toolbar">
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            aria-label="Season"
            disabled={STATIC_DEMO}
          >
            {YEARS.map((y) => (
              <option key={y}>{y}</option>
            ))}
          </select>
          <select
            value={round ?? ''}
            onChange={(e) => setRound(Number(e.target.value))}
            disabled={!rounds.data?.length}
            aria-label="Grand Prix"
          >
            {(rounds.data ?? []).map((r) => (
              <option key={r.round} value={r.round}>
                R{r.round} · {r.name} ({r.state})
              </option>
            ))}
          </select>
        </div>
        <Status loading={rounds.loading} error={rounds.error} hint="Loading the calendar…" />
        <Status loading={forecast.loading} error={forecast.error} hint="Computing the forecast…" />
      </section>

      {!data && !forecast.loading && !forecast.error && !rounds.loading && !rounds.error && (
        <Empty>
          {rounds.data?.length === 0
            ? 'No forecasts are available for this season.'
            : 'Pick a round to see its forecast.'}
        </Empty>
      )}

      {data && (
        <div className="grid-2">
          <Card title={`${data.year} ${data.race_name}`}>
            <p className="muted">{STATE_TEXT[data.state]}</p>
            <div className="table-wrap">
              <ForecastTable data={data} />
            </div>
          </Card>
          <ModelCard data={data} />
        </div>
      )}
    </div>
  )
}

function ForecastTable({ data }: { data: Prediction }) {
  const finished = data.state === 'finished'
  const hasGrid = data.state !== 'upcoming'
  return (
    <table>
      <thead>
        <tr>
          <th>Pred.</th>
          <th>Driver</th>
          <th>Team</th>
          {hasGrid && <th>Grid</th>}
          <th>Win</th>
          <th>Podium</th>
          <th title="Mean finishing position over the simulated orders">Exp. pos.</th>
          {finished && <th>Result</th>}
        </tr>
      </thead>
      <tbody>
        {data.drivers.map((d) => (
          <tr key={d.driver_id}>
            <td>{d.predicted_position}</td>
            <td>
              <strong>{d.code}</strong>
            </td>
            <td className="muted">{d.constructor_id.replaceAll('_', ' ')}</td>
            {hasGrid && <td>{d.grid ?? MISSING}</td>}
            <td>
              <Bar p={d.p_win} />
            </td>
            <td>
              <Bar p={d.p_podium} />
            </td>
            <td>{d.expected_position.toFixed(1)}</td>
            {finished && <td>{d.actual_position === null ? MISSING : `P${d.actual_position}`}</td>}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Bar({ p }: { p: number }) {
  return (
    <div className="bar">
      <div style={{ width: `${p * 100}%` }} />
      <span>{pct(p)}</span>
    </div>
  )
}

function ModelCard({ data }: { data: Prediction }) {
  const cv = data.model.cv
  const rows: [string, number, number][] = [
    ['Rank correlation with the result', cv.spearman, cv.grid_baseline_spearman],
    ['Winner picked', cv.winner_hit, cv.grid_baseline_winner_hit],
    ['Podium places picked', cv.podium_overlap, cv.grid_baseline_podium_overlap],
  ]
  return (
    <Card title="How far to trust this">
      {data.score && (
        <p>
          This race: rank correlation {data.score.spearman.toFixed(2)}, winner{' '}
          {data.score.winner_predicted ? 'predicted' : 'missed'} (given {pct(data.score.winner_p_win)}).
          {data.in_training_data && ' The model was trained on this race, so this is not a fair test.'}
        </p>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>On {cv.n_test_races} held-out races</th>
              <th>Model</th>
              <th title="Predicting that everyone finishes where they start">Grid order</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, model, grid], i) => (
              <tr key={label}>
                <td>{label}</td>
                <td>{i === 0 ? model.toFixed(2) : pct(model)}</td>
                <td>{i === 0 ? grid.toFixed(2) : pct(grid)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted">
        {data.variant === 'pre_quali' ? 'Form-only model' : 'Post-qualifying model'}, a LightGBM ranker trained on{' '}
        {data.model.n_races} races ({data.model.years[0]} to {data.model.years[1]}) on{' '}
        {data.model.trained_at.slice(0, 10)}. Probabilities come from 20,000 simulated finishing orders. It knows
        nothing about weather, penalties, upgrades or reliability.
      </p>
    </Card>
  )
}
