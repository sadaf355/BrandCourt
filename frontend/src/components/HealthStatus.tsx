import { useQuery } from '@tanstack/react-query'
import { Activity, CheckCircle2, CircleAlert, Database, RefreshCw, Server } from 'lucide-react'
import { getHealth } from '../lib/api'

export function HealthStatus() {
  const query = useQuery({ queryKey: ['api-health'], queryFn: ({ signal }) => getHealth(signal), retry: 1, refetchInterval: 30_000 })
  const health = query.data
  const apiOkay = health?.status === 'ok'
  const dbOkay = health?.database === 'connected'

  return (
    <section className="health-panel" aria-labelledby="health-heading">
      <div className="section-heading">
        <div><p className="eyebrow">FOUNDATION CHECK</p><h2 id="health-heading">System status</h2></div>
        <button className="icon-button" onClick={() => void query.refetch()} aria-label="Refresh system status" title="Refresh status"><RefreshCw size={16} className={query.isFetching ? 'spin' : ''} /></button>
      </div>
      <div className="health-grid">
        <div className="health-item">
          <div className="health-item__icon"><Server size={18} /></div>
          <div className="health-item__copy"><span>API service</span><strong>{query.isPending ? 'Checking…' : apiOkay ? 'Operational' : 'Unavailable'}</strong></div>
          <span className={`status-dot ${query.isPending ? 'status-dot--loading' : apiOkay ? 'status-dot--good' : 'status-dot--bad'}`} />
        </div>
        <div className="health-item">
          <div className="health-item__icon"><Database size={18} /></div>
          <div className="health-item__copy"><span>Database</span><strong>{query.isPending ? 'Checking…' : !health ? 'Unknown' : health.database === 'connected' ? 'Connected' : health.database === 'not_configured' ? 'Not configured' : 'Unavailable'}</strong></div>
          <span className={`status-dot ${query.isPending ? 'status-dot--loading' : dbOkay ? 'status-dot--good' : 'status-dot--warn'}`} />
        </div>
      </div>
      {query.isError && <p className="health-note health-note--error"><CircleAlert size={14} /> Cannot reach the API. Start the FastAPI server and check VITE_API_BASE_URL.</p>}
      {health && health.database === 'not_configured' && <p className="health-note"><Activity size={14} /> API is reachable. Add DATABASE_URL to backend/.env to enable database checks.</p>}
      {health && health.database === 'connected' && <p className="health-note health-note--success"><CheckCircle2 size={14} /> API and database are responding.</p>}
    </section>
  )
}
