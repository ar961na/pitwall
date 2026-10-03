import type { Corner, Minisector } from '../api/types'
import { SERIES_DASH } from '../lib/format'

interface Props {
  distance: number[]
  x: number[]
  y: number[]
  minisectors: Minisector[]
  corners: Corner[]
  colorA: string
  colorB: string
}

/** Racing line coloured by who was faster in each minisector, with corner numbers. */
export function TrackMap({ distance, x, y, minisectors, corners, colorA, colorB }: Props) {
  const pad = 600
  const minX = Math.min(...x) - pad
  const maxX = Math.max(...x) + pad
  const minY = Math.min(...y) - pad
  const maxY = Math.max(...y) + pad
  // SVG y grows downwards, track coordinates grow upwards: flip y.
  const fy = (v: number) => maxY + minY - v

  const width = (maxX - minX) / 90
  const segments = minisectors.map((ms, i) => {
    const idx = distance.flatMap((d, k) => (d >= ms.start_m && d <= ms.end_m ? [k] : []))
    // Overlap one sample into the next minisector so segments join without gaps,
    // and close the loop on the last one (the position feed starts a touch late).
    const next = i === minisectors.length - 1 ? 0 : Math.min(idx[idx.length - 1] + 1, x.length - 1)
    const pts = [...idx, next].map((k) => `${x[k]},${fy(y[k])}`).join(' ')
    return (
      <polyline
        key={i}
        points={pts}
        fill="none"
        stroke={ms.gain_b_s > 0 ? colorB : colorA}
        strokeWidth={width}
        // B's minisectors are dashed like B's lines in the charts, so colour isn't the only cue
        strokeDasharray={
          ms.gain_b_s > 0
            ? SERIES_DASH[1]
                ?.split(' ')
                .map((n) => Number(n) * width * 0.5)
                .join(' ')
            : undefined
        }
        strokeLinecap="butt"
        strokeLinejoin="round"
      >
        <title>
          {Math.round(ms.start_m)} to {Math.round(ms.end_m)} m: {ms.gain_b_s > 0 ? 'B' : 'A'} faster by{' '}
          {Math.abs(ms.gain_b_s).toFixed(3)} s
        </title>
      </polyline>
    )
  })

  const fontSize = (maxX - minX) / 35
  return (
    <svg
      viewBox={`${minX} ${minY} ${maxX - minX} ${maxY - minY}`}
      className="track-map"
      role="img"
      aria-label="Track map: solid segments where driver A was faster, dashed where driver B was faster"
    >
      {segments}
      {corners.map((c) => (
        <text key={`${c.number}${c.letter}`} x={c.x} y={fy(c.y)} fontSize={fontSize} className="corner-label">
          {c.number}
          {c.letter}
        </text>
      ))}
    </svg>
  )
}
