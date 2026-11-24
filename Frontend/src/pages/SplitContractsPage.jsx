import { useMemo, useState } from 'react'
import { useDashboard } from '../dashboardContext'

const initialCollaborators = [
  { id: 1, name: 'Kamga Beats', role: 'Artist (Lead)', momo: '+237 677 41 90 12', share: 70 },
  { id: 2, name: 'Producer Njoh', role: 'Producer', momo: '+237 679 88 14 55', share: 30 },
]

export default function SplitContractsPage() {
  const { language } = useDashboard()
  const fr = language === 'fr'
  const [track, setTrack] = useState('Midnight Rain')
  const [collaborators, setCollaborators] = useState(initialCollaborators)
  const [copied, setCopied] = useState(false)
  const [pinSent, setPinSent] = useState(false)

  const total = useMemo(() => collaborators.reduce((sum, person) => sum + Number(person.share || 0), 0), [collaborators])
  const netSale = 480

  const setShare = (id, share) => {
    setCollaborators((items) => items.map((item) => item.id === id ? { ...item, share: Math.max(0, Math.min(100, Number(share))) } : item))
  }

  const addCollaborator = () => {
    setCollaborators((items) => [...items, { id: Date.now(), name: '', role: '', momo: '', share: 0 }])
  }

  const removeCollaborator = (id) => {
    if (collaborators.length <= 2) return
    setCollaborators((items) => items.filter((item) => item.id !== id))
  }

  const copyContractId = async () => {
    try { await navigator.clipboard?.writeText('CH-SPL-2026-8841F') } catch { /* clipboard unavailable */ }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  const updateCollaborator = (id, field, value) => {
    setCollaborators((items) => items.map((item) => item.id === id ? { ...item, [field]: value } : item))
  }

  const activeTracks = ['Midnight Rain', 'Buea Town Vibe', 'Douala Dusk', 'Bamenda Sunrise']

  return (
    <main className="split-page">
      <section className="split-heading">
        <div>
          <span className="split-eyebrow">CamerHits • {fr ? 'Partages démo' : 'Demo splits'}</span>
          <h1>{fr ? 'Constructeur de contrat de partage' : 'Direct Split Contract Builder'}</h1>
          <p>{fr ? 'Morceau :' : 'Track:'} <strong>{track}</strong> — {fr ? 'Les pourcentages doivent totaliser 100 %.' : 'Shares must total 100%.'}</p>
        </div>
        <span className={total === 100 ? 'split-total valid' : 'split-total'}>{fr ? 'Total' : 'Total'}: {total}%</span>
      </section>

      <section className="split-layout">
        <div className="split-collaborators-panel">
          <div className="split-panel-heading">
            <h2>{fr ? 'Collaborateurs et numéros MoMo' : 'Collaborators & MoMo Numbers'}</h2>
            <button type="button" className="split-outline-button" onClick={addCollaborator}><span className="material-icon">person_add</span>{fr ? 'Ajouter' : 'Add Collaborator'}</button>
          </div>

          <div className="split-track-select">
            <label><span>{fr ? 'Morceau' : 'Track'}</span><select value={track} onChange={(event) => setTrack(event.target.value)}>{activeTracks.map((item) => <option key={item}>{item}</option>)}</select></label>
          </div>

          <div className="collaborator-rows">
            {collaborators.map((person) => (
              <article className="collaborator-row" key={person.id}>
                <div className="collaborator-fields">
                  <label><span>{fr ? 'Nom' : 'Name'}</span><input value={person.name} onChange={(event) => updateCollaborator(person.id, 'name', event.target.value)} placeholder={fr ? 'Nom du collaborateur' : 'Collaborator name'} /></label>
                  <label><span>{fr ? 'Rôle' : 'Role'}</span><input value={person.role} onChange={(event) => updateCollaborator(person.id, 'role', event.target.value)} placeholder={fr ? 'Rôle' : 'Role'} /></label>
                  <label><span>MoMo</span><input value={person.momo} onChange={(event) => updateCollaborator(person.id, 'momo', event.target.value)} placeholder='+237...' /></label>
                </div>
                <div className="share-control">
                  <strong>{person.share}%</strong>
                  {collaborators.length > 2 && <button type="button" className="remove-collaborator" onClick={() => removeCollaborator(person.id)} aria-label={fr ? 'Supprimer le collaborateur' : 'Remove collaborator'}><span className="material-icon">close</span></button>}
                  <input type="range" min="0" max="100" value={person.share} onChange={(event) => setShare(person.id, event.target.value)} aria-label={`${person.name || (fr ? 'Collaborateur' : 'Collaborator')} share`} />
                </div>
              </article>
            ))}
          </div>

          {total !== 100 && <div className="split-error" role="alert"><span className="material-icon">error</span><span>{fr ? 'Le total doit être exactement 100 % avant la confirmation.' : 'Split total must equal 100% before confirmation.'}</span></div>}

          <div className="split-chart-card">
            <div className="split-chart"><div className="donut" style={{ '--share': `${total === 100 ? 360 : 360 * (total / 100)}deg` }}><div><strong>{total}%</strong><span>{fr ? 'total' : 'total'}</span></div></div></div>
            <div className="split-legend">
              {collaborators.map((person) => <div key={person.id}><span className="legend-dot" /><span><strong>{person.name || (fr ? 'Sans nom' : 'Unnamed')}</strong> — {person.share}%</span></div>)}
            </div>
            <div className="sale-breakdown"><span>{fr ? 'Par vente de 500 XAF (net 480 XAF)' : 'Per 500 XAF sale (480 XAF net)'}</span>{collaborators.map((person) => <strong key={person.id}>{Math.round(netSale * person.share / 100)} XAF — {person.name || (fr ? 'Sans nom' : 'Unnamed')}</strong>)}</div>
          </div>
        </div>

        <aside className="split-preview-panel">
          <div className="split-preview-heading"><div><span className="material-icon">lock</span><h2>{fr ? 'Aperçu du contrat' : 'Contract Preview'}</h2></div><span className="demo-badge">DEMO</span></div>
          <div className="contract-id"><span>ID: CH-SPL-2026-8841F</span><button type="button" onClick={copyContractId} aria-label={fr ? 'Copier l’identifiant' : 'Copy Contract ID'}><span className="material-icon">content_copy</span></button></div>
          {copied && <small className="copy-status" role="status">{fr ? 'Identifiant copié' : 'Contract ID copied'}</small>}
          <div className="contract-copy">
            <p>{fr ? 'Pour chaque vente directe ou licence B2B du morceau' : 'Every direct fan purchase or B2B licensing payout for'} <strong>“{track}”</strong>, {fr ? 'le partage démo suivant serait appliqué après les frais affichés :' : 'the following demo split would be applied after the displayed rail fee:'}</p>
            <ul>{collaborators.map((person) => <li key={person.id}><strong>{person.share}%</strong> — {person.name || (fr ? 'Collaborateur sans nom' : 'Unnamed collaborator')} ({person.momo || 'No MoMo'})</li>)}</ul>
            <p className="demo-copy">{fr ? 'Ceci est un contrat démo local. Aucun numéro n’a été signé et aucun paiement n’a été effectué.' : 'This is a local demo contract. No PIN was signed and no payment was made.'}</p>
          </div>

          <div className="signature-status">
            <span>{fr ? 'Statut des signatures' : 'Signature Status'}</span>
            {collaborators.map((person) => (
              <div className="signature-row" key={person.id}><strong>{person.name || (fr ? 'Sans nom' : 'Unnamed')}</strong><span className={person.share > 0 && total === 100 ? 'pending-signature' : 'unsigned-signature'}>{total === 100 ? (fr ? 'Prêt pour PIN démo' : 'Ready for demo PIN') : (fr ? 'En attente' : 'Pending')}</span></div>
            ))}
          </div>

          <button type="button" className="primary-button full split-sign-button" disabled={total !== 100} onClick={() => setPinSent(true)}>
            <span className="material-icon">pin</span>{pinSent ? (fr ? 'Demande démo envoyée' : 'Demo Request Sent') : (fr ? 'Envoyer pour PIN démo' : 'Send for Demo PIN')}
          </button>
        </aside>
      </section>
    </main>
  )
}
