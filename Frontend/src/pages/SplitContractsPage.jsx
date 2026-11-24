import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiClient } from '../services/api/client'
import { useDashboard } from '../dashboardContext'

const initialCollaborators = [
  { id: 1, name: 'KOCEE', role: 'Artist (Lead)', momo: '+237 677 41 90 12', share: 70 },
  { id: 2, name: 'Producer Njoh', role: 'Producer', momo: '+237 679 88 14 55', share: 30 },
]

export default function SplitContractsPage() {
  const { language } = useDashboard()
  const fr = language === 'fr'
  const [track, setTrack] = useState('Midnight Rain')
  const [collaborators, setCollaborators] = useState(initialCollaborators)
  const [copied, setCopied] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const [contractRecord, setContractRecord] = useState(null)
  const [createFormOpen, setCreateFormOpen] = useState(false)
  const [signFormOpen, setSignFormOpen] = useState(false)
  const [artistPhone, setArtistPhone] = useState('')
  const [artistPin, setArtistPin] = useState('')
  const [signerPhone, setSignerPhone] = useState('')
  const [signerPin, setSignerPin] = useState('')
  const [requestError, setRequestError] = useState('')
  const [requestBusy, setRequestBusy] = useState(false)

  useEffect(() => {
    const contractId = searchParams.get('contract')
    if (!contractId) return
    let cancelled = false
    apiClient.get(`/split-contracts/${contractId}`)
      .then(({ data }) => { if (!cancelled) { setContractRecord(data); setTrack(data.track_title); setCollaborators(data.participants.map((person, index) => ({ id: index + 1, name: person.name, role: person.role, momo: person.momo_number, share: person.share_percent, signed: person.signed }))) } })
      .catch((error) => { if (!cancelled) setRequestError(error.response?.data?.error?.message || (fr ? 'Impossible de charger le contrat.' : 'Could not load this contract.')) })
    return () => { cancelled = true }
  }, [searchParams, fr])

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
    const inviteUrl = contractRecord ? `${window.location.origin}/split-contracts?contract=${contractRecord.id}` : ''
    if (!inviteUrl) return
    try { await navigator.clipboard?.writeText(inviteUrl) } catch { /* clipboard unavailable */ }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  const updateCollaborator = (id, field, value) => {
    setCollaborators((items) => items.map((item) => item.id === id ? { ...item, [field]: value } : item))
  }

  const activeTracks = ['Midnight Rain', 'Buea Town Vibe', 'Douala Dusk', 'Bamenda Sunrise']

  const apiError = (error) => error.response?.data?.error?.message || error.response?.data?.detail || (fr ? 'Une erreur est survenue. Réessayez.' : 'Something went wrong. Please try again.')

  const createContract = async (event) => {
    event.preventDefault()
    setRequestBusy(true)
    setRequestError('')
    try {
      const { data: login } = await apiClient.post('/auth/login', { phone: artistPhone, pin: artistPin })
      const payload = {
        track_title: track,
        participants: collaborators.map((person) => ({ name: person.name, role: person.role, phone: person.momo, momo_number: person.momo, share_percent: person.share })),
      }
      const { data } = await apiClient.post('/split-contracts', payload, { headers: { Authorization: `Bearer ${login.access_token}` } })
      setContractRecord(data)
      setCollaborators(data.participants.map((person, index) => ({ id: index + 1, name: person.name, role: person.role, momo: person.momo_number, share: person.share_percent, signed: person.signed })))
      setCreateFormOpen(false)
      setArtistPin('')
      setSearchParams({ contract: data.id })
    } catch (error) {
      setRequestError(apiError(error))
    } finally {
      setRequestBusy(false)
    }
  }

  const signContract = async (event) => {
    event.preventDefault()
    if (!contractRecord) return
    setRequestBusy(true)
    setRequestError('')
    try {
      const { data: login } = await apiClient.post('/auth/login', { phone: signerPhone, pin: signerPin })
      const { data } = await apiClient.post(`/split-contracts/${contractRecord.id}/sign`, {}, { headers: { Authorization: `Bearer ${login.access_token}` } })
      setContractRecord(data)
      setCollaborators(data.participants.map((person, index) => ({ id: index + 1, name: person.name, role: person.role, momo: person.momo_number, share: person.share_percent, signed: person.signed })))
      setSignFormOpen(false)
      setSignerPin('')
    } catch (error) {
      setRequestError(apiError(error))
    } finally {
      setRequestBusy(false)
    }
  }

  return (
    <main className="split-page">
      <section className="split-heading">
        <div>
          <span className="split-eyebrow">CamerHits • {fr ? 'Partages directs' : 'Direct splits'}</span>
          <h1>{fr ? 'Constructeur de contrat de partage' : 'Direct Split Contract Builder'}</h1>
          <p>{fr ? 'Morceau :' : 'Track:'} <strong>{track}</strong> — {fr ? 'Les pourcentages doivent totaliser 100 %.' : 'Shares must total 100%.'}</p>
        </div>
        <span className={total === 100 ? 'split-total valid' : 'split-total'}>{fr ? 'Total' : 'Total'}: {total}%</span>
      </section>

      <section className="split-layout">
        <div className="split-collaborators-panel">
          <div className="split-panel-heading">
            <h2>{fr ? 'Collaborateurs et numéros MoMo' : 'Collaborators & MoMo Numbers'}</h2>
            <button type="button" className="split-outline-button" onClick={addCollaborator} disabled={Boolean(contractRecord)}><span className="material-icon">person_add</span>{fr ? 'Ajouter' : 'Add Collaborator'}</button>
          </div>

          <div className="split-track-select">
            <label><span>{fr ? 'Morceau' : 'Track'}</span><select value={track} disabled={Boolean(contractRecord)} onChange={(event) => setTrack(event.target.value)}>{activeTracks.map((item) => <option key={item}>{item}</option>)}</select></label>
          </div>

          <div className="collaborator-rows">
            {collaborators.map((person) => (
              <article className="collaborator-row" key={person.id}>
                <div className="collaborator-fields">
                  <label><span>{fr ? 'Nom' : 'Name'}</span><input value={person.name} disabled={Boolean(contractRecord)} onChange={(event) => updateCollaborator(person.id, 'name', event.target.value)} placeholder={fr ? 'Nom du collaborateur' : 'Collaborator name'} /></label>
                  <label><span>{fr ? 'Rôle' : 'Role'}</span><input value={person.role} disabled={Boolean(contractRecord)} onChange={(event) => updateCollaborator(person.id, 'role', event.target.value)} placeholder={fr ? 'Rôle' : 'Role'} /></label>
                  <label><span>{fr ? 'Téléphone CamerHits / MoMo' : 'CamerHits / MoMo phone'}</span><input value={person.momo} disabled={Boolean(contractRecord)} onChange={(event) => updateCollaborator(person.id, 'momo', event.target.value)} placeholder='+237...' /></label>
                </div>
                <div className="share-control">
                  <strong>{person.share}%</strong>
                  {collaborators.length > 2 && <button type="button" className="remove-collaborator" disabled={Boolean(contractRecord)} onClick={() => removeCollaborator(person.id)} aria-label={fr ? 'Supprimer le collaborateur' : 'Remove collaborator'}><span className="material-icon">close</span></button>}
                  <input type="range" min="0" max="100" value={person.share} disabled={Boolean(contractRecord)} onChange={(event) => setShare(person.id, event.target.value)} aria-label={`${person.name || (fr ? 'Collaborateur' : 'Collaborator')} share`} />
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
          <div className="split-preview-heading"><div><span className="material-icon">lock</span><h2>{fr ? 'Contrat de partage' : 'Split Contract'}</h2></div><span className={`contract-status ${contractRecord?.status || 'draft'}`}>{contractRecord ? (contractRecord.status === 'signed' ? (fr ? 'Signé' : 'Signed') : (fr ? 'En attente' : 'Pending')) : (fr ? 'Non créé' : 'Not created')}</span></div>
          <div className="contract-id"><span>{contractRecord ? `ID: ${contractRecord.id}` : (fr ? 'Le contrat sera créé à la demande' : 'Contract will be created when requested')}</span>{contractRecord && <button type="button" onClick={copyContractId} aria-label={fr ? 'Copier le lien de signature' : 'Copy signing link'}><span className="material-icon">content_copy</span></button>}</div>
          {copied && <small className="copy-status" role="status">{fr ? 'Lien de signature copié' : 'Signing link copied'}</small>}
          <div className="contract-copy">
            <p>{fr ? 'Répartition proposée pour les ventes directes ou licences B2B du morceau' : 'Proposed split for direct fan purchases or B2B licensing payouts for'} <strong>“{track}”</strong>:</p>
            <ul>{collaborators.map((person) => <li key={person.id}><strong>{person.share}%</strong> — {person.name || (fr ? 'Collaborateur sans nom' : 'Unnamed collaborator')} ({person.momo || 'No MoMo'})</li>)}</ul>
            <p className="service-note">{contractRecord ? (fr ? 'Les collaborateurs signent avec leur compte CamerHits. Cette signature confirme le partage; aucun paiement MoMo n’est déclenché.' : 'Collaborators sign with their CamerHits accounts. This records agreement to the split; it does not initiate a MoMo payment.') : (fr ? 'Créez le contrat pour générer un lien de signature sécurisé.' : 'Create the contract to generate a secure signing link.')}</p>
          </div>

          <div className="signature-status">
            <span>{fr ? 'Statut des signatures' : 'Signature Status'}</span>
            {collaborators.map((person) => (
              <div className="signature-row" key={person.id}><strong>{person.name || (fr ? 'Sans nom' : 'Unnamed')}</strong><span className={person.signed ? 'pending-signature' : 'unsigned-signature'}>{person.signed ? (fr ? 'Signé' : 'Signed') : contractRecord ? (fr ? 'En attente' : 'Awaiting signature') : (fr ? 'En attente de création' : 'Awaiting contract')}</span></div>
            ))}
          </div>
          {requestError && <p className="form-error" role="alert">{requestError}</p>}
          {!contractRecord && (createFormOpen ? <form className="dashboard-form signing-form" onSubmit={createContract}><p>{fr ? 'Connectez-vous avec votre compte Artiste CamerHits. Chaque collaborateur doit avoir un compte actif et le numéro indiqué ci-dessus doit correspondre à son compte.' : 'Sign in with the artist CamerHits account. Every collaborator needs an active account, and the phone listed above must match that account.'}</p><label><span>{fr ? 'Téléphone de l’artiste' : 'Artist phone number'}</span><input autoComplete="tel" value={artistPhone} onChange={(event) => setArtistPhone(event.target.value)} placeholder="+237 6XX XXX XXX" required /></label><label><span>{fr ? 'PIN du compte CamerHits' : 'CamerHits account PIN'}</span><input type="password" inputMode="numeric" autoComplete="current-password" minLength="4" maxLength="6" value={artistPin} onChange={(event) => setArtistPin(event.target.value)} required /></label><small>{fr ? 'N’entrez jamais votre PIN MoMo ici. Utilisez uniquement le PIN de connexion CamerHits.' : 'Never enter your MoMo PIN here. Use only your CamerHits sign-in PIN.'}</small><div className="form-actions"><button type="button" className="secondary-button" onClick={() => setCreateFormOpen(false)}>{fr ? 'Annuler' : 'Cancel'}</button><button type="submit" className="primary-button" disabled={requestBusy || total !== 100}>{requestBusy ? (fr ? 'Création…' : 'Creating…') : (fr ? 'Créer le contrat' : 'Create Contract')}</button></div></form> : <button type="button" className="primary-button full split-sign-button" disabled={total !== 100} onClick={() => { setCreateFormOpen(true); setRequestError('') }}><span className="material-icon">description</span>{fr ? 'Créer le contrat et demander les signatures' : 'Create Contract & Request Signatures'}</button>)}
          {contractRecord && contractRecord.status !== 'signed' && (signFormOpen ? <form className="dashboard-form signing-form" onSubmit={signContract}><p>{fr ? 'Chaque collaborateur signe avec son propre compte CamerHits. Le PIN de connexion sera vérifié par le serveur et ne sera pas enregistré dans le contrat.' : 'Each collaborator signs with their own CamerHits account. The server verifies the sign-in PIN; it is not stored with the contract.'}</p><label><span>{fr ? 'Votre numéro CamerHits' : 'Your CamerHits phone number'}</span><input autoComplete="tel" value={signerPhone} onChange={(event) => setSignerPhone(event.target.value)} placeholder="+237 6XX XXX XXX" required /></label><label><span>{fr ? 'PIN du compte CamerHits' : 'CamerHits account PIN'}</span><input type="password" inputMode="numeric" autoComplete="current-password" minLength="4" maxLength="6" value={signerPin} onChange={(event) => setSignerPin(event.target.value)} required /></label><small>{fr ? 'N’entrez jamais votre PIN MoMo ici. Utilisez uniquement le PIN de connexion CamerHits.' : 'Never enter your MoMo PIN here. Use only your CamerHits sign-in PIN.'}</small><div className="form-actions"><button type="button" className="secondary-button" onClick={() => setSignFormOpen(false)}>{fr ? 'Annuler' : 'Cancel'}</button><button type="submit" className="primary-button" disabled={requestBusy}>{requestBusy ? (fr ? 'Vérification…' : 'Verifying…') : (fr ? 'Signer le contrat' : 'Sign Contract')}</button></div></form> : <button type="button" className="primary-button full split-sign-button" onClick={() => { setSignFormOpen(true); setRequestError('') }}><span className="material-icon">draw</span>{fr ? 'Signer avec le compte CamerHits' : 'Sign with CamerHits Account'}</button>)}
          {contractRecord?.status === 'signed' && <p className="service-note">{fr ? 'Tous les collaborateurs ont signé ce contrat.' : 'All collaborators have signed this contract.'}</p>}
        </aside>
      </section>
    </main>
  )
}
