import { useCallback, useEffect, useState } from 'react'
import { getInspection } from './api'
import { Sidebar, type PageKey } from './components/Sidebar'
import { Icon } from './components/ui'
import { History } from './pages/History'
import { ModelPerformance } from './pages/ModelPerformance'
import { NewInspection } from './pages/NewInspection'
import { Overview } from './pages/Overview'
import { QualityReports } from './pages/QualityReports'
import { ReferenceComparison } from './pages/ReferenceComparison'
import { Settings } from './pages/Settings'
import type { InspectionResult } from './types'

const PAGE_TITLES: Record<PageKey, string> = {
  overview: 'Genel Bakış',
  inspection: 'Yeni PCB Analizi',
  history: 'Analiz Geçmişi',
  reference: 'Referans Karşılaştırma',
  reports: 'Kalite Raporları',
  models: 'Model Performansı',
  settings: 'Sistem Ayarları',
}

const VALID_PAGES = Object.keys(PAGE_TITLES) as PageKey[]

function pageFromHash(): PageKey {
  const raw = window.location.hash.replace(/^#\/?/, '') as PageKey
  return VALID_PAGES.includes(raw) ? raw : 'overview'
}

function App() {
  const [page, setPage] = useState<PageKey>(pageFromHash)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [result, setResult] = useState<InspectionResult | null>(null)
  const [referenceSeed, setReferenceSeed] = useState<{ name: string; nonce: number } | null>(null)
  const [openError, setOpenError] = useState<string | null>(null)

  const navigate = useCallback((next: PageKey) => {
    setPage(next)
    window.location.hash = `/${next}`
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  useEffect(() => {
    const onHashChange = () => setPage(pageFromHash())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const openInspection = useCallback(async (id: string) => {
    setOpenError(null)
    try {
      const loaded = await getInspection(id)
      setResult(loaded)
      navigate('inspection')
    } catch (err) {
      setOpenError(err instanceof Error ? err.message : 'Analiz açılamadı')
    }
  }, [navigate])

  const useReference = useCallback((name: string) => {
    setReferenceSeed({ name, nonce: Date.now() })
    setResult(null)
    navigate('inspection')
  }, [navigate])

  return (
    <div className="app-shell">
      <Sidebar
        active={page}
        onNavigate={navigate}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="app-main">
        <header className="topbar">
          <button
            type="button"
            className="icon-btn menu-btn"
            onClick={() => setSidebarOpen(true)}
            aria-label="Menüyü aç"
          >
            <Icon name="reference" size={20} />
          </button>
          <div className="breadcrumb">
            <span>AOI Kalite Kontrol</span>
            <Icon name="chevron" size={13} />
            <strong>{PAGE_TITLES[page]}</strong>
          </div>
          <div className="topbar-status">
            <span className="status-dot" />
            Sistem Çevrimiçi
          </div>
        </header>

        <main className="page-container">
          {openError && (
            <div className="inline-error" role="alert">
              {openError}
              <button type="button" className="link-btn" onClick={() => setOpenError(null)}>Kapat</button>
            </div>
          )}

          {page === 'overview' && <Overview onNavigate={navigate} onOpenInspection={(id) => void openInspection(id)} />}
          {page === 'inspection' && (
            <NewInspection
              key={referenceSeed?.nonce ?? 'inspection'}
              result={result}
              onResult={setResult}
              initialReference={referenceSeed?.name}
            />
          )}
          {page === 'history' && <History onOpenInspection={(id) => void openInspection(id)} />}
          {page === 'reference' && <ReferenceComparison onUseReference={useReference} />}
          {page === 'reports' && <QualityReports />}
          {page === 'models' && <ModelPerformance />}
          {page === 'settings' && <Settings />}
        </main>
      </div>
    </div>
  )
}

export default App
