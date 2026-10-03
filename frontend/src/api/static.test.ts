import { describe, expect, it } from 'vitest'
import { labelForParams, optimizePath, rememberParams, staticPath } from './static'

// Same vectors as backend/tests/test_static_demo.py — change both together.
const VECTORS: [string, string][] = [
  ['/health', 'health.json'],
  ['/events/2026', 'events/2026.json'],
  ['/sessions/11361/drivers', 'sessions/11361/drivers.json'],
  ['/sessions/11361/compare?a=VER&b=NOR', 'sessions/11361/compare__a=VER__b=NOR.json'],
  ['/sessions/11361/compare?b=NOR&a=VER', 'sessions/11361/compare__a=VER__b=NOR.json'],
  ['/sessions/9920/strategy/calibrate', 'sessions/9920/strategy/calibrate.json'],
]

describe('staticPath', () => {
  it.each(VECTORS)('%s -> %s', (path, expected) => {
    expect(staticPath(path)).toBe(expected)
  })
})

describe('optimizePath', () => {
  it('matches the backend naming', () => {
    expect(optimizePath('calibrated-9920', 2, 2000)).toBe('strategy/optimize/calibrated-9920__stops2__sims2000.json')
  })
})

describe('params registry', () => {
  it('recognises unedited params and rejects edited ones', () => {
    const params = { total_laps: 53, pit_loss_s: 25.43, compounds: { SOFT: { offset_s: 0.05 } } }
    rememberParams('calibrated-1', params)
    expect(labelForParams(params)).toBe('calibrated-1')
    expect(labelForParams({ ...params, pit_loss_s: 20 })).toBeUndefined()
  })
})
