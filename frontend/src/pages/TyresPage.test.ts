import { describe, expect, it } from 'vitest'
import { groupByCompound } from './TyresPage'

const point = (driver: string, compound: string) => ({
  driver,
  compound,
  team: 't',
  lap: 1,
  stint: 1,
  tyre_life: 1,
  lap_time_s: 90,
  corrected_s: 0,
  predicted_s: 90,
})

describe('groupByCompound', () => {
  const points = [point('VER', 'SOFT'), point('NOR', 'SOFT'), point('VER', 'HARD')]

  it('groups all drivers when no driver is selected', () => {
    const g = groupByCompound(points, '')
    expect(g.SOFT).toHaveLength(2)
    expect(g.HARD).toHaveLength(1)
  })

  it('keeps only the selected driver', () => {
    const g = groupByCompound(points, 'NOR')
    expect(g.SOFT).toHaveLength(1)
    expect(g.HARD).toBeUndefined()
  })
})
