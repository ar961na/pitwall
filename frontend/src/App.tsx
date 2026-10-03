import { useEffect, useState } from 'react'
import { REPO_URL, STATIC_DEMO } from './api/static'
import { DemoBanner } from './components/DemoBanner'
import { PredictPage } from './pages/PredictPage'
import { StrategyPage } from './pages/StrategyPage'
import { TelemetryPage } from './pages/TelemetryPage'
import { TyresPage } from './pages/TyresPage'

const PAGES = {
  telemetry: { label: 'Telemetry', component: TelemetryPage },
  tyres: { label: 'Tyres', component: TyresPage },
  strategy: { label: 'Strategy', component: StrategyPage },
  predict: { label: 'Predict', component: PredictPage },
} as const
type PageId = keyof typeof PAGES

// The page lives in the URL hash (#strategy) so reloads and shared links keep it.
function pageFromHash(): PageId {
  const id = window.location.hash.slice(1)
  return id in PAGES ? (id as PageId) : 'telemetry'
}

export default function App() {
  const [page, setPage] = useState<PageId>(pageFromHash)

  useEffect(() => {
    const onHash = () => setPage(pageFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const Page = PAGES[page].component
  return (
    <>
      <header className="topbar">
        <span className="logo">
          pit<span>wall</span>
        </span>
        <nav>
          {(Object.keys(PAGES) as PageId[]).map((id) => (
            <a key={id} href={`#${id}`} className={id === page ? 'active' : undefined}>
              {PAGES[id].label}
            </a>
          ))}
        </nav>
      </header>
      <main>
        {STATIC_DEMO && <DemoBanner />}
        <Page />
      </main>
      <footer className="footer">
        Data: <a href="https://openf1.org">OpenF1</a> and <a href="https://github.com/jolpica/jolpica-f1">Jolpica F1</a>{' '}
        (both CC BY-NC-SA 4.0), circuit info: <a href="https://multiviewer.app">MultiViewer</a>. Methods and sources:{' '}
        <a href={`${REPO_URL}/blob/main/docs/REFERENCES.md`}>docs/REFERENCES.md</a>.
        <br />
        Unofficial, non-commercial project; not associated with Formula 1. F1 and related marks are trade marks of
        Formula One Licensing B.V.
      </footer>
    </>
  )
}
