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

describe('bandRows', () => {
  it('pairs the low and high quantiles per tyre age', async () => {
    const { bandRows } = await import('./TyresPage')
    const rows = bandRows({ tyre_life: [1, 2], lo: [-1, -0.5], median: [0, 0.2], hi: [1, 1.5] })
    expect(rows).toEqual([
      { tyre_life: 1, band: [-1, 1], median: 0 },
      { tyre_life: 2, band: [-0.5, 1.5], median: 0.2 },
    ])
  })
})
