import type {
  CompareResponse,
  DegradationResponse,
  Driver,
  EventInfo,
  OptimizeRequest,
  OptimizeResponse,
  RaceParams,
} from './types'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
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

export const api = {
  events: (year: number) => request<EventInfo[]>(`/events/${year}`),
  drivers: (sessionKey: number) => request<Driver[]>(`/sessions/${sessionKey}/drivers`),
  compare: (sessionKey: number, a: string, b: string) =>
    request<CompareResponse>(`/sessions/${sessionKey}/compare?a=${a}&b=${b}`),
  degradation: (sessionKey: number) => request<DegradationResponse>(`/sessions/${sessionKey}/degradation`),
  strategyDefaults: () => request<RaceParams>('/strategy/defaults'),
  calibrate: (sessionKey: number, driver?: string) =>
    request<RaceParams>(`/sessions/${sessionKey}/strategy/calibrate${driver ? `?driver=${driver}` : ''}`),
  optimize: (body: OptimizeRequest) =>
    request<OptimizeResponse>('/strategy/optimize', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}
