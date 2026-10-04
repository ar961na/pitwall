// Static demo mode (GitHub Pages): instead of calling the FastAPI backend, read JSON files that CI
// pre-computed with `python -m pitwall.static_demo`. File names MUST match static_demo.py.

import { ApiError } from './errors'

export const STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === 'true'
export const REPO_URL = 'https://github.com/ar961na/pitwall'

const ROOT = `${import.meta.env.BASE_URL}static-api/`

/** "/sessions/1/compare?b=NOR&a=VER" -> "sessions/1/compare__a=VER__b=NOR.json" */
export function staticPath(path: string): string {
  const [base, query] = path.replace(/^\/+|\/+$/g, '').split('?')
  if (!query) return `${base}.json`
  return `${base}__${query.split('&').sort().join('__')}.json`
}

export function optimizePath(label: string, maxStops: number, nSims: number): string {
  return `strategy/optimize/${label}__stops${maxStops}__sims${nSims}.json`
}

export async function fetchStatic<T>(relative: string, notFound: string): Promise<T> {
  const res = await fetch(ROOT + relative)
  if (!res.ok) throw new ApiError(404, notFound)
  return res.json() as Promise<T>
}

export const NOT_IN_DEMO =
  'Not included in the static demo, which only has a few pre-computed sessions. Run pitwall locally ' +
  `for every session and live parameters: ${REPO_URL}`

// Parameter sets the snapshot has optimiser results for, keyed by their exact JSON.
// The Strategy page passes back the very object it received, so equal JSON = unedited params.
const knownParams = new Map<string, string>()

export function rememberParams(label: string, params: unknown) {
  knownParams.set(JSON.stringify(params), label)
}

export function labelForParams(params: unknown): string | undefined {
  return knownParams.get(JSON.stringify(params))
}

export interface Manifest {
  generated_at: string
  sessions: { session_key: number; name: string; drivers: string[] }[]
  optimize: { max_stops: number[]; n_sims: number }
}
