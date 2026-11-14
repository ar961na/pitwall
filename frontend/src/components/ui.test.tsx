import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { formatLapTime } from '../lib/format'
import { CompoundChip } from './ui'

describe('formatLapTime', () => {
  it('formats seconds as m:ss.mmm', () => {
    expect(formatLapTime(83.088)).toBe('1:23.088')
    expect(formatLapTime(65.5)).toBe('1:05.500')
  })
})

describe('CompoundChip', () => {
  it('shows the compound initial and stint length', () => {
    render(<CompoundChip compound="MEDIUM" laps={25} />)
    expect(screen.getByText('M')).toBeInTheDocument()
    expect(screen.getByText('25')).toBeInTheDocument()
  })
})
