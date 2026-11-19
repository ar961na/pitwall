import { describe, expect, it } from 'vitest'
import type { PredictRound } from '../api/types'
import { defaultRound } from './PredictPage'

const r = (round: number, state: PredictRound['state']): PredictRound => ({
  round,
  state,
  name: `GP ${round}`,
  date: '',
})

describe('defaultRound', () => {
  it('picks the next race that has not finished', () => {
    expect(defaultRound([r(1, 'finished'), r(2, 'qualified'), r(3, 'upcoming')])).toBe(2)
  })
  it('falls back to the last race when the season is over', () => {
    expect(defaultRound([r(1, 'finished'), r(2, 'finished')])).toBe(2)
  })
  it('returns null without rounds', () => {
    expect(defaultRound([])).toBeNull()
  })
})
