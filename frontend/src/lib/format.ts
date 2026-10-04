// Theme-aware colours (CSS variables from index.css and styles/tokens.css), usable in SVG too.
export const COMPOUND_COLORS: Record<string, string> = {
  SOFT: 'var(--tyre-soft)',
  MEDIUM: 'var(--tyre-medium)',
  HARD: 'var(--tyre-hard)',
  INTERMEDIATE: 'var(--tyre-inter)',
  WET: 'var(--tyre-wet)',
}

// Dash patterns so series differ by more than colour (ui.md: don't rely on colour alone).
export const SERIES_DASH = [undefined, '6 3', '2 2'] as const

/** 83.088 -> "1:23.088" */
export function formatLapTime(s: number): string {
  const m = Math.floor(s / 60)
  return `${m}:${(s - m * 60).toFixed(3).padStart(6, '0')}`
}

/** Placeholder for missing values in tables. */
export const MISSING = 'n/a'
