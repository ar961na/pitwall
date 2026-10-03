import { Card, TaskCallout } from '../components/ui'

/** FRONTEND TASK R2: docs/tasks/R2-predict-page.md (after TASK 5 serves predictions). */
export function PredictPage() {
  return (
    <div className="page">
      <Card title="Race prediction">
        <TaskCallout task="TASK 5 + R2">
          Train the finishing-order model (TASK 5), serve it from{' '}
          <code>
            GET /api/predict/{'{year}'}/{'{round}'}
          </code>
          , then show the predicted grid → finish here with win / podium probabilities. Run it on Saturday night, check
          it on Sunday.
        </TaskCallout>
      </Card>
    </div>
  )
}
