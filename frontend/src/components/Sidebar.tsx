import { Icon } from './ui'

export type PageKey =
  | 'overview'
  | 'inspection'
  | 'history'
  | 'reference'
  | 'reports'
  | 'models'
  | 'settings'

const NAV_GROUPS: Array<{ label: string; items: Array<{ key: PageKey; label: string; icon: string }> }> = [
  {
    label: 'KALİTE KONTROL',
    items: [
      { key: 'overview', label: 'Genel Bakış', icon: 'overview' },
      { key: 'inspection', label: 'Yeni PCB Analizi', icon: 'inspection' },
      { key: 'history', label: 'Analiz Geçmişi', icon: 'history' },
      { key: 'reference', label: 'Referans Karşılaştırma', icon: 'reference' },
    ],
  },
  {
    label: 'YÖNETİM',
    items: [
      { key: 'reports', label: 'Kalite Raporları', icon: 'reports' },
      { key: 'models', label: 'Model Performansı', icon: 'model' },
      { key: 'settings', label: 'Sistem Ayarları', icon: 'settings' },
    ],
  },
]

export function Sidebar({
  active,
  onNavigate,
  open,
  onClose,
}: {
  active: PageKey
  onNavigate: (page: PageKey) => void
  open: boolean
  onClose: () => void
}) {
  return (
    <>
      {open && <button className="sidebar-backdrop" aria-label="Menüyü kapat" onClick={onClose} />}
      <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <span className="brand-mark"><Icon name="shield" size={22} /></span>
          <div>
            <strong>PCB INSPECTION</strong>
            <span>AI · AOI Quality Control</span>
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          Sistem Çevrimiçi
        </div>

        <nav className="nav" aria-label="Ana menü">
          {NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.label}>
              <div className="nav-group-label">{group.label}</div>
              {group.items.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className={`nav-item ${active === item.key ? 'nav-item-active' : ''}`}
                  onClick={() => {
                    onNavigate(item.key)
                    onClose()
                  }}
                  aria-current={active === item.key ? 'page' : undefined}
                >
                  <Icon name={item.icon} size={18} />
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="operator">
            <span className="avatar">QK</span>
            <div>
              <strong>Kalite Kontrol</strong>
              <span>Yerel oturum</span>
            </div>
          </div>
          <span className="version">v0.2.0 · fotoğraf tabanlı</span>
        </div>
      </aside>
    </>
  )
}
