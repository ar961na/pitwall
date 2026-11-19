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

describe('cornerLabel', () => {
  it('labels published corners by number and letter, detected zones with B', async () => {
    const { cornerLabel } = await import('../lib/format')
    expect(cornerLabel({ number: 4, letter: 'A', source: 'published' })).toBe('4A')
    expect(cornerLabel({ number: 3, letter: '', source: 'detected' })).toBe('B3')
  })
})
