import { useEffect, useMemo, useRef, useState } from 'react'
import { mediaUrl } from '../api'
import { defectLabel } from '../labels'
import type { Detection, InspectionResult } from '../types'
import { Icon } from './ui'

const MIN_ZOOM = 1
const MAX_ZOOM = 6

export function PcbViewer({ result }: { result: InspectionResult }) {
  const [zoom, setZoom] = useState(MIN_ZOOM)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [mode, setMode] = useState<'annotated' | 'original'>('annotated')
  const [showBoxes, setShowBoxes] = useState(true)
  const [classFilter, setClassFilter] = useState('all')
  const [selected, setSelected] = useState<number | null>(null)
  const stageRef = useRef<HTMLDivElement | null>(null)
  const drag = useRef({ active: false, x: 0, y: 0, ox: 0, oy: 0 })

  const classes = useMemo(
    () => Array.from(new Set(result.defects.map((item) => item.class_name))).sort(),
    [result.defects],
  )

  const visibleDefects = useMemo(
    () =>
      result.defects
        .map((defect, index) => ({ defect, index }))
        .filter(({ defect }) => classFilter === 'all' || defect.class_name === classFilter),
    [result.defects, classFilter],
  )

  const selectedDefect: Detection | null = selected === null ? null : result.defects[selected] ?? null

  const fit = () => {
    setZoom(MIN_ZOOM)
    setOffset({ x: 0, y: 0 })
  }

  const changeZoom = (delta: number) => {
    setZoom((current) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, current + delta)))
  }

  useEffect(() => {
    const stage = stageRef.current
    if (!stage) return
    const onWheel = (event: WheelEvent) => {
      event.preventDefault()
      setZoom((current) =>
        Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, current + (event.deltaY < 0 ? 0.25 : -0.25))),
      )
    }
    stage.addEventListener('wheel', onWheel, { passive: false })
    return () => stage.removeEventListener('wheel', onWheel)
  }, [])

  useEffect(() => {
    setZoom(MIN_ZOOM)
    setOffset({ x: 0, y: 0 })
    setSelected(null)
    setClassFilter('all')
    setMode('annotated')
  }, [result.image_id])

  const imageUrl =
    mode === 'annotated'
      ? mediaUrl(result.annotated_image_path) ?? mediaUrl(result.original_image_path)
      : mediaUrl(result.original_image_path)

  return (
    <div className="viewer">
      <div className="viewer-toolbar">
        <div className="segmented" role="group" aria-label="Görüntü modu">
          <button
            type="button"
            className={mode === 'annotated' ? 'segment-active' : ''}
            onClick={() => setMode('annotated')}
          >
            İşaretli
          </button>
          <button
            type="button"
            className={mode === 'original' ? 'segment-active' : ''}
            onClick={() => setMode('original')}
          >
            Orijinal
          </button>
        </div>

        <label className="toggle">
          <input
            type="checkbox"
            checked={showBoxes}
            onChange={(event) => setShowBoxes(event.target.checked)}
          />
          Kutu göster
        </label>

        <select
          className="select"
          value={classFilter}
          onChange={(event) => setClassFilter(event.target.value)}
          aria-label="Kusur sınıfı filtresi"
        >
          <option value="all">Tüm sınıflar ({result.defects.length})</option>
          {classes.map((name) => (
            <option key={name} value={name}>{defectLabel(name)}</option>
          ))}
        </select>

        <div className="viewer-controls">
          <button type="button" className="icon-btn" onClick={() => changeZoom(-0.5)} title="Uzaklaştır">
            <Icon name="zoomOut" size={17} />
          </button>
          <span className="zoom-label">%{Math.round(zoom * 100)}</span>
          <button type="button" className="icon-btn" onClick={() => changeZoom(0.5)} title="Yakınlaştır">
            <Icon name="zoomIn" size={17} />
          </button>
          <button type="button" className="icon-btn" onClick={fit} title="Ekrana sığdır">
            <Icon name="fit" size={17} />
          </button>
        </div>
      </div>

      <div
        className="viewer-stage"
        ref={stageRef}
        onPointerDown={(event) => {
          drag.current = {
            active: true,
            x: event.clientX,
            y: event.clientY,
            ox: offset.x,
            oy: offset.y,
          }
          event.currentTarget.setPointerCapture(event.pointerId)
        }}
        onPointerMove={(event) => {
          if (!drag.current.active) return
          setOffset({
            x: drag.current.ox + event.clientX - drag.current.x,
            y: drag.current.oy + event.clientY - drag.current.y,
          })
        }}
        onPointerUp={(event) => {
          drag.current.active = false
          event.currentTarget.releasePointerCapture(event.pointerId)
        }}
        onPointerCancel={() => { drag.current.active = false }}
      >
        {imageUrl ? (
          <div
            className="viewer-canvas"
            style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})` }}
          >
            <img src={imageUrl} alt="PCB görüntüsü" draggable={false} />
            {mode === 'annotated' &&
              showBoxes &&
              visibleDefects.map(({ defect, index }) => {
                const [x1, y1, x2, y2] = defect.bbox
                const left = (x1 / result.image_width) * 100
                const top = (y1 / result.image_height) * 100
                const width = ((x2 - x1) / result.image_width) * 100
                const height = ((y2 - y1) / result.image_height) * 100
                return (
                  <button
                    type="button"
                    key={`${defect.class_name}-${index}`}
                    className={`defect-box ${selected === index ? 'defect-box-selected' : ''}`}
                    style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }}
                    title={`${defectLabel(defect.class_name)} · %${(defect.confidence * 100).toFixed(1)}`}
                    onPointerDown={(event) => event.stopPropagation()}
                    onClick={() => setSelected(index)}
                  >
                    <span>{defectLabel(defect.class_name)}</span>
                  </button>
                )
              })}
          </div>
        ) : (
          <div className="viewer-placeholder">Görüntü bulunamadı</div>
        )}
      </div>

      <div className="viewer-footer">
        {selected !== null && selectedDefect ? (
          <div className="defect-detail">
            <div>
              <strong>{defectLabel(selectedDefect.class_name)}</strong>
              <span className="muted">
                #{selected + 1} · {selectedDefect.class_name} · sınıf kimliği {selectedDefect.class_id}
              </span>
            </div>
            <div><span>Güven</span><strong>%{(selectedDefect.confidence * 100).toFixed(1)}</strong></div>
            <div className="mono">
              <span>Kutu</span>
              <strong>{selectedDefect.bbox.map((value) => value.toFixed(0)).join(', ')}</strong>
            </div>
            <div className="detail-note">
              İlgili bölgeyi yakınlaştırarak fiziksel inceleme yapın. Bu kutu modelin tespitidir;
              kesin kusur doğrulaması görsel kontroldür.
            </div>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>
              <Icon name="close" size={14} /> Kapat
            </button>
          </div>
        ) : (
          <span className="muted viewer-hint">
            Yakınlaştırmak için tekerlek, kaydırmak için sürükleme kullanın. Detay için bir kutuya tıklayın.
          </span>
        )}
      </div>
    </div>
  )
}
