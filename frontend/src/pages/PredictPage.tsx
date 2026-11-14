import { Card, Empty } from '../components/ui'

export function PredictPage() {
  return (
    <div className="page">
      <Card title="Race prediction">
        <Empty>
          No race predictor has been trained yet. Once one is, this page shows the predicted finishing order with win
          and podium probabilities after qualifying.
        </Empty>
      </Card>
    </div>
  )
}
