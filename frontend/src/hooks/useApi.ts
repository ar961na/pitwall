import { useEffect, useState } from 'react'

export interface ApiState<T> {
  data?: T
  error?: string
  loading: boolean
}

/**
 * Run an async request whenever `deps` change and track loading / error / data.
 *
 * Pass `null` as the fetcher to skip (e.g. while a dropdown is still empty).
 * The `cancelled` flag stops a slow, outdated response from overwriting a newer one
 * when the user changes the selection mid-request.
 */
export function useApi<T>(fetcher: (() => Promise<T>) | null, deps: unknown[]): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({ loading: fetcher !== null })

  useEffect(() => {
    if (!fetcher) {
      setState({ loading: false })
      return
    }
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: undefined }))
    fetcher()
      .then((data) => !cancelled && setState({ data, loading: false }))
      .catch((e: Error) => !cancelled && setState({ error: e.message, loading: false }))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
