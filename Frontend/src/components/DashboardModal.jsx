import { useEffect, useRef } from 'react'

export default function DashboardModal({ open, title, eyebrow, onClose, children, size = '' }) {
  const panelRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const previous = document.activeElement
    panelRef.current?.querySelector('button, input, select, textarea')?.focus()
    const handleKey = (event) => {
      if (event.key === 'Escape') onClose()
      if (event.key !== 'Tab') return
      const nodes = panelRef.current?.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href]')
      if (!nodes?.length) return
      const first = nodes[0]
      const last = nodes[nodes.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventEvent?.(); event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', handleKey)
    return () => { document.removeEventListener('keydown', handleKey); previous?.focus() }
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section ref={panelRef} className={`dashboard-modal ${size}`} role="dialog" aria-modal="true" aria-labelledby="dashboard-modal-title">
        <header className="modal-header"><div>{eyebrow && <span className="modal-eyebrow">{eyebrow}</span>}<h2 id="dashboard-modal-title">{title}</h2></div><button className="modal-close" type="button" onClick={onClose} aria-label="Close dialog">×</button></header>
        <div className="modal-body">{children}</div>
      </section>
    </div>
  )
}
