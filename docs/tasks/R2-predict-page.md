# Task R2: Predict page (React + API design)

**Prereq:** Task 5 serving `GET /api/predict/{year}/{round}`.
**File:** `frontend/src/pages/PredictPage.tsx`

## Goal

Pick a race weekend and show the prediction: grid position → predicted finish, P(win) and
P(podium) as bars, and (after the race) the actual result next to it, with a score.

## Steps

1. **Design the API contract first.** Write the response type in `src/api/types.ts` *before* the
   backend route. Agree on field names and on the meaning of "position" for DNFs.
2. Add `api.predict(year, round)` to `src/api/client.ts`.
3. Reuse `SessionPicker` with `sessionNames={['Qualifying']}`. The prediction needs qualifying
   to be finished.
4. Table with team colours (the drivers endpoint has them), a probability bar (copy `.bar` from
   the Strategy page), and arrows for places gained/lost vs grid.
5. When the race is finished, fetch the actual result and show Spearman ρ and whether the
   winner was right.
6. Handle 501 (no model yet) and 404 gracefully. `ApiError.status` is available.

## Stretch

- A "season scoreboard" chart from `predictions/scores.csv` served by a new endpoint.
- Optimistic loading skeletons instead of the "Loading…" text.

## References

Tags point to [docs/REFERENCES.md](../REFERENCES.md).

- [D2] Jolpica results (CC BY-NC-SA 4.0): show the credit on the page
- [M15] Brier score, [M16] calibration
