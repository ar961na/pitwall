import { fetchStatic, type Manifest, REPO_URL } from '../api/static'
import { useApi } from '../hooks/useApi'

/** Shown only in the GitHub Pages build: explains what the static snapshot contains. */
export function DemoBanner() {
  const manifest = useApi(() => fetchStatic<Manifest>('manifest.json', 'no manifest'), [])
  const m = manifest.data
  return (
    <div className="demo-banner" role="note">
      <strong>Static demo.</strong> Pre-computed by CI
      {m && <> on {m.generated_at.slice(0, 10)}</>} for {m ? m.sessions.length : 'a few'} sessions
      {m && <> ({m.sessions.map((s) => s.name).join(', ')})</>}. Telemetry: top-3 drivers; strategy: unedited parameters
      only. For every session and live simulation, <a href={REPO_URL}>run pitwall locally</a>.
    </div>
  )
}
