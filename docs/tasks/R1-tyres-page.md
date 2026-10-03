# Task R1: Build the Tyres page (React)

**File:** `frontend/src/pages/TyresPage.tsx`
**API (already works):** `GET /api/sessions/{session_key}/degradation` → `DegradationResponse` in `src/api/types.ts`
**Check:** `npm run typecheck && npm test`, then look at it in the browser.

## Goal

A scatter of fuel- and driver-corrected lap time against tyre age, coloured by compound, with the
fitted degradation line per compound, plus a summary table.

## React in 5 minutes (what you need for this task)

- A **component** is a function that returns JSX. It re-runs ("re-renders") whenever its props or
  state change.
- **`useState`** holds a value across renders: `const [x, setX] = useState(0)`. Calling `setX`
  schedules a re-render.
- **`useEffect`** runs side effects *after* render (fetching, subscriptions). Its dependency array
  says when to re-run.
- **This repo's pattern:** `useApi(fetcher, deps)` in `src/hooks/useApi.ts` wraps
  useEffect + useState for you. Read it, because it's 30 lines and contains the important
  "cancelled" trick for race conditions.
- **Lists** need a stable `key` prop: `{rows.map(r => <tr key={r.id}>…</tr>)}`.

## Steps

1. Read `TelemetryPage.tsx` top to bottom. It's the reference for every pattern you need.
2. `const deg = useApi(sessionKey ? () => api.degradation(sessionKey) : null, [sessionKey])` and show
   `<Status loading=… error=… />`.
3. Scatter: recharts `ScatterChart` with one `<Scatter>` per compound. Group `deg.data.points` by
   compound with `useMemo`. Colours come from `COMPOUND_COLORS` in `src/lib/format.ts`.
4. Lines: `curves[compound]` → `{tyre_life, corrected_s}`. Recharts can mix `Scatter` and `Line`
   in a `ComposedChart`.
5. Table: compound chip | deg (s/lap) | offset vs reference | number of laps.
6. Add a driver filter (`<select>`) that highlights one driver's points. That gives you derived
   state with `useMemo`.
7. Write one vitest test for any pure helper you extract (e.g. `groupByCompound`).

<details><summary>Hint: chart skeleton</summary>

```tsx
<ResponsiveContainer width="100%" height={360}>
  <ComposedChart margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
    <CartesianGrid stroke="var(--grid)" />
    <XAxis type="number" dataKey="tyre_life" name="Tyre age" stroke="var(--muted)" />
    <YAxis type="number" dataKey="corrected_s" domain={['auto', 'auto']} stroke="var(--muted)" />
    <Tooltip />
    {Object.entries(byCompound).map(([c, pts]) => (
      <Scatter key={c} data={pts} fill={COMPOUND_COLORS[c]} fillOpacity={0.5} />
    ))}
  </ComposedChart>
</ResponsiveContainer>
```
</details>

## Bonus: understand the lint warnings

`npm run lint` warns about "setState in effect" in `TelemetryPage` and `SessionPicker`. Read
https://react.dev/learn/you-might-not-need-an-effect and refactor one of them away (e.g. derive
the default drivers during render instead of syncing them in an effect).

## References

Tags point to [docs/REFERENCES.md](../REFERENCES.md).

- React docs: https://react.dev/learn (state, effects), https://react.dev/learn/you-might-not-need-an-effect
- Recharts API: https://recharts.github.io/en-US/api
- Data credit: the page shows OpenF1-derived data [D1]; the app footer carries the attribution
