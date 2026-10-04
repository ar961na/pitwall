import { ApiError } from './errors'
import {
  fetchStatic,
  labelForParams,
  NOT_IN_DEMO,
  optimizePath,
  rememberParams,
  STATIC_DEMO,
  staticPath,
} from './static'
import type {
  CompareResponse,
  DegradationResponse,
  Driver,
  EventInfo,
  OptimizeRequest,
  OptimizeResponse,
  RaceParams,
} from './types'

export { ApiError }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (STATIC_DEMO) return fetchStatic<T>(staticPath(path), NOT_IN_DEMO)

  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    // FastAPI puts the reason in {"detail": ...}
    let detail: unknown = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* body wasn't JSON */
    }
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json() as Promise<T>
}

async function optimize(body: OptimizeRequest): Promise<OptimizeResponse> {
  if (!STATIC_DEMO) {
    return request<OptimizeResponse>('/strategy/optimize', { method: 'POST', body: JSON.stringify(body) })
  }
  const label = labelForParams(body.params)
  if (!label) {
    throw new ApiError(501, `Edited parameters need the live simulator. ${NOT_IN_DEMO}`)
  }
  return fetchStatic(optimizePath(label, body.max_stops, body.n_sims), NOT_IN_DEMO)
}

export const api = {
  events: (year: number) => request<EventInfo[]>(`/events/${year}`),
  drivers: (sessionKey: number) => request<Driver[]>(`/sessions/${sessionKey}/drivers`),
  compare: (sessionKey: number, a: string, b: string) =>
    request<CompareResponse>(`/sessions/${sessionKey}/compare?a=${a}&b=${b}`),
  degradation: (sessionKey: number) => request<DegradationResponse>(`/sessions/${sessionKey}/degradation`),
  strategyDefaults: async () => {
    const params = await request<RaceParams>('/strategy/defaults')
    if (STATIC_DEMO) rememberParams('defaults', params)
    return params
  },
  calibrate: async (sessionKey: number, driver?: string) => {
    const params = await request<RaceParams>(
      `/sessions/${sessionKey}/strategy/calibrate${driver ? `?driver=${driver}` : ''}`,
    )
    if (STATIC_DEMO && !driver) rememberParams(`calibrated-${sessionKey}`, params)
    return params
  },
  optimize,
}
