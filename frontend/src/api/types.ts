// Shapes of the JSON the FastAPI backend returns. Keep in sync with backend/src/pitwall/api/routes.

export interface SessionRef {
  session_key: number
  name: string // "Race", "Qualifying", "Sprint", "Practice 1", ...
  date: string
  completed: boolean
}

export interface EventInfo {
  round: number
  meeting_key: number
  name: string
  circuit: string
  country: string
  date: string
  sessions: SessionRef[]
}

export interface Driver {
  number: number
  code: string
  name: string
  team: string
  color: string
  position: number | null
}

export interface LapInfo {
  driver: string
  lap_number: number
  lap_time_s: number
}

export interface Corner {
  number: number
  letter: string
  distance: number
  x: number
  y: number
}

export interface Minisector {
  start_m: number
  end_m: number
  gain_b_s: number
}

export type CornerRow = Record<string, number | null>

export interface CompareResponse {
  session: string
  a: LapInfo
  b: LapInfo
  // column-oriented: channels.speed_a[i] is the speed at channels.distance[i]
  channels: Record<string, (number | boolean | null)[]>
  minisectors: Minisector[]
  corners: Corner[]
  corner_analysis: CornerRow[]
}

export type Compound = 'SOFT' | 'MEDIUM' | 'HARD'

export interface CompoundParams {
  offset_s: number
  deg_s_per_lap: number
  cliff_age: number
  cliff_s_per_lap2: number
}

export interface RaceParams {
  total_laps: number
  base_lap_time_s: number
  lap_coef_s: number
  pit_loss_s: number
  sc_prob_per_lap: number
  sc_min_laps: number
  sc_max_laps: number
  sc_lap_factor: number
  sc_pit_loss_factor: number
  lap_noise_s: number
  compounds: Record<string, CompoundParams>
}

export interface StrategyResult {
  label: string
  stints: { compound: string; laps: number }[]
  pit_laps: number[]
  n_stops: number
  mean_s: number
  std_s: number
  p10_s: number
  p50_s: number
  p90_s: number
  p_best: number
  gap_s: number
  expected_no_sc_s: number
  reactive_gain_s: number
  clean_lap_times_s?: number[]
}

export interface OptimizeRequest {
  params: RaceParams
  max_stops: number
  min_stint: number
  n_sims: number
  seed: number
}

export interface OptimizeResponse {
  params: RaceParams
  results: StrategyResult[]
}

export interface DegradationResponse {
  session: string
  model: {
    reference_compound: string
    driver_offset: Record<string, number>
    compound_offset: Record<string, number>
    deg_per_lap: Record<string, number>
    lap_coef: number
    rmse: number
    n_laps: number
  }
  curves: Record<string, { tyre_life: number[]; corrected_s: number[] }>
  cliffs: Record<string, number>
  laps_per_compound: Record<string, number>
  points: {
    driver: string
    team: string
    lap: number
    stint: number
    compound: string
    tyre_life: number
    lap_time_s: number
    corrected_s: number
    predicted_s: number
  }[]
}

export type RoundState = 'finished' | 'qualified' | 'upcoming'

export interface PredictRound {
  round: number
  name: string
  date: string
  state: RoundState
}

export interface PredictedDriver {
  driver_id: string
  code: string
  constructor_id: string
  grid: number | null
  predicted_position: number
  expected_position: number
  p_win: number
  p_podium: number
  actual_position: number | null
}

export interface Prediction {
  year: number
  round: number
  race_name: string
  state: RoundState
  variant: 'post_quali' | 'pre_quali'
  in_training_data: boolean
  score: { spearman: number; winner_predicted: boolean; winner_p_win: number } | null
  model: {
    trained_at: string
    years: [number, number]
    n_races: number
    // race-ordered cross-validation, with the same metrics for plain grid order
    cv: Record<string, number>
  }
  drivers: PredictedDriver[]
}
