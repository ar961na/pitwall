export const COMPOUND_COLORS: Record<string, string> = {
  SOFT: '#ff3333',
  MEDIUM: '#ffd12e',
  HARD: '#e8e8e8',
  INTERMEDIATE: '#39b54a',
  WET: '#0067ad',
}

export function formatLapTime(s: number): string {
  const m = Math.floor(s / 60)
  return `${m}:${(s - m * 60).toFixed(3).padStart(6, '0')}`
}
