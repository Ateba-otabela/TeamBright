import { useState } from 'react'
import DashboardModal from './DashboardModal'
import { useDashboard } from '../dashboardContext'

const tracks = ['Midnight Rain', 'Buea Town Vibe', 'Douala Dusk', 'Bamenda Sunrise']
const destinations = [
  { id: 'dj-nzo', name: 'DJ Nzo', type: 'DJ', city: 'Douala' },
  { id: 'hit-radio', name: 'Hit FM Cameroon', type: 'Station radio', city: 'Douala' },
  { id: 'crtv', name: 'CRTV Channel 1', type: 'Chaîne TV', city: 'Yaoundé' },
  { id: 'buea-sound', name: 'Buea Sound Radio', type: 'Station radio', city: 'Buea' },
]

export default function DashboardActions({ activeModal, setActiveModal }) {
  const { language, t } = useDashboard()
  const fr = language === 'fr'
  const [upload, setUpload] = useState({ title: '', artist: 'KOCEE', genre: 'Afropop', file: null })
  const [uploadError, setUploadError] = useState('')
  const [uploadDone, setUploadDone] = useState(false)
  const [diagnosisTrack, setDiagnosisTrack] = useState('Midnight Rain')
  const [analysisDone, setAnalysisDone] = useState(false)
  const [collaborators, setCollaborators] = useState([{ name: 'KOCEE', share: '70' }, { name: 'Producer Njoh', share: '30' }])
  const [contractTrack, setContractTrack] = useState('Buea Town Vibe')
  const [contractStep, setContractStep] = useState('form')
  const [contractError, setContractError] = useState('')
  const [destinationSearch, setDestinationSearch] = useState('')
  const [destination, setDestination] = useState('')
  const [trackSearch, setTrackSearch] = useState('')
  const [broadcastTrack, setBroadcastTrack] = useState('')
  const [broadcastStep, setBroadcastStep] = useState('form')
  const [broadcastError, setBroadcastError] = useState('')

  const close = () => setActiveModal(null)

  const submitUpload = (event) => {
    event.preventEvent?.()
    event.preventDefault()
    setUploadError('')
    setUploadDone(false)
    if (!upload.title.trim()) return setUploadError(fr ? 'Veuillez saisir le titre du morceau.' : 'Enter a song title.')
    if (!upload.file) return setUploadError(fr ? 'Veuillez sélectionner un fichier audio.' : 'Select an audio file.')
    const ok = /\.(mp3|wav|m4a|aac|flac)$/i.test(upload.file.name)
    if (!ok) return setUploadError(fr ? 'Format accepté : MP3, WAV, M4A, AAC ou FLAC.' : 'Accepted types: MP3, WAV, M4A, AAC, or FLAC.')
    setUploadDone(true)
  }

  const submitContract = (event) => {
    event.preventDefault()
    setContractError('')
    if (collaborators.some((person) => !person.name.trim() || person.share === '')) return setContractError(fr ? 'Chaque collaborateur doit avoir un nom et un pourcentage.' : 'Every collaborator needs a name and percentage.')
    const total = collaborators.reduce((sum, person) => sum + Number(person.share), 0)
    if (!Number.isFinite(total) || total !== 100) return setContractError(fr ? `Le total doit être exactement 100 % (actuellement ${total} %).` : `Shares must total exactly 100% (currently ${total}%).`)
    setContractStep('review')
  }

  const submitBroadcast = (event) => {
    event.preventDefault()
    setBroadcastError('')
    const destinationMatch = destinations.find((item) => item.name.toLowerCase() === destinationSearch.trim().toLowerCase())
    const trackMatch = tracks.find((track) => track.toLowerCase() === trackSearch.trim().toLowerCase())
    if (!destinationMatch) return setBroadcastError(fr ? 'Sélectionnez une destination valide dans la liste.' : 'Select a valid destination from the list.')
    if (!trackMatch) return setBroadcastError(fr ? 'Sélectionnez un morceau valide dans la liste.' : 'Select a valid track from the list.')
    setDestination(destinationMatch.name)
    setBroadcastTrack(trackMatch)
    setBroadcastStep('review')
  }

  return (
    <>
      <DashboardModal open={activeModal === 'upload'} title={fr ? 'Téléverser un son' : 'Upload Song'} eyebrow={t.uploadFlow} onClose={close}>
        {uploadDone ? <div className="success-panel" role="status"><span className="material-icon">check_circle</span><div><strong>{fr ? 'Fichier prêt' : 'File ready'}</strong><p>{fr ? 'Le fichier est sélectionné. Le service de téléversement n’est pas connecté.' : 'The file is selected. The upload service is not connected.'}</p></div></div> : <form className="dashboard-form" onSubmit={submitUpload}>
          <label><span>{fr ? 'Titre du morceau' : 'Song title'} *</span><input value={upload.title} onChange={(event) => setUpload({ ...upload, title: event.target.value })} required /></label>
          <div className="form-grid"><label><span>{fr ? 'Interprète' : 'Artist'}</span><input value={upload.artist} onChange={(event) => setUpload({ ...upload, artist: event.target.value })} /></label><label><span>{fr ? 'Genre' : 'Genre'}</span><input value={upload.genre} onChange={(event) => setUpload({ ...upload, genre: event.target.value })} /></label></div>
          <label><span>{fr ? 'Fichier audio' : 'Audio file'} *</span><input type="file" accept=".mp3,.wav,.m4a,.aac,.flac,audio/*" onChange={(event) => setUpload({ ...upload, file: event.target.files?.[0] || null })} /></label>
          {uploadError && <p className="form-error" role="alert">{uploadError}</p>}
          <button className="primary-button full" type="submit"><span className="material-icon">upload</span>{fr ? 'Vérifier le fichier' : 'Check File'}</button>
        </form>}
      </DashboardModal>

      <DashboardModal open={activeModal === 'diagnosis'} title={fr ? 'Diagnostic IA' : 'AI Diagnosis'} eyebrow={t.analysisFlow} onClose={close}>
        {!analysisDone ? <form className="dashboard-form" onSubmit={(event) => { event.preventDefault(); setAnalysisDone(true) }}>
          <label><span>{fr ? 'Choisir ou fournir un morceau' : 'Choose or provide a song'}</span><select value={diagnosisTrack} onChange={(event) => setDiagnosisTrack(event.target.value)}>{tracks.map((track) => <option key={track}>{track}</option>)}</select></label>
          <p className="form-note">{fr ? 'Le résultat affiché est un exemple; le service d’analyse n’est pas connecté ici.' : 'The result shown is an example; the analysis service is not connected here.'}</p>
          <button className="primary-button full" type="submit">{fr ? 'Afficher l’analyse' : 'View Analysis'}</button>
        </form> : <div className="diagnosis-result"><div className="form-note">{fr ? 'Résultat exemple — aucune analyse réelle effectuée' : 'Example result — no live analysis performed'}</div><h3>{diagnosisTrack}</h3><strong className="score-large">41.2</strong><p>{fr ? 'Exemple : l’introduction ralentit l’entrée du refrain.' : 'Example finding: the intro delays the chorus entry.'}</p><ul><li>{fr ? 'Éditer pour raccourcir l’introduction.' : 'Trim the introduction.'}</li><li>{fr ? 'Tester le titre à 500 XAF.' : 'Test the track price at 500 XAF.'}</li></ul><button className="secondary-button" type="button" onClick={() => setActiveModal('inspect')}>{fr ? 'Voir les détails' : 'Inspect Diagnosis'}</button></div>}
      </DashboardModal>

      <DashboardModal open={activeModal === 'inspect'} title={fr ? 'Diagnostic détaillé' : 'Detailed Diagnosis'} eyebrow={t.analysisFlow} onClose={close} size="wide">
        <div className="diagnosis-result"><div className="form-note">{fr ? 'Résultat exemple — aucune analyse réelle effectuée' : 'Example result — no live analysis performed'}</div><div className="diagnosis-heading"><div><span>{fr ? 'Morceau concerné' : 'Relevant track'}</span><h3>Midnight Rain</h3></div><strong className="score-large">41.2</strong></div><h4>{fr ? 'Constats' : 'Findings'}</h4><ul><li>{fr ? 'Le refrain commence à 44 s, soit 26 s plus tard que la référence.' : 'Chorus begins at 44s, 26s later than the benchmark.'}</li><li>{fr ? 'La mise à prix actuelle peut réduire l’achat impulsif.' : 'The current price may reduce impulse purchasing.'}</li></ul><h4>{fr ? 'Prochaines étapes suggérées' : 'Suggested next steps'}</h4><ol><li>{fr ? 'Faire un montage radio de moins de 24 s avant le refrain.' : 'Create a radio edit reaching the chorus in under 24s.'}</li><li>{fr ? 'Tester une offre directe à 500 XAF.' : 'Test a direct fan offer at 500 XAF.'}</li><li>{fr ? 'Lancer une campagne DJ locale.' : 'Launch a targeted local DJ campaign.'}</li></ol></div>
      </DashboardModal>

      <DashboardModal open={activeModal === 'split'} title={fr ? 'Créer un contrat de partage' : 'Create Split Contract'} eyebrow={t.contractFlow} onClose={close}>
        {contractStep === 'form' ? <form className="dashboard-form" onSubmit={submitContract}>
          <label><span>{fr ? 'Morceau' : 'Track'} *</span><select value={contractTrack} onChange={(event) => setContractTrack(event.target.value)}>{tracks.map((track) => <option key={track}>{track}</option>)}</select></label>
          <div className="collaborator-list">{collaborators.map((person, index) => <div className="form-grid" key={index}><label><span>{fr ? 'Collaborateur' : 'Collaborator'}</span><input value={person.name} onChange={(event) => setCollaborators((items) => items.map((item, i) => i === index ? { ...item, name: event.target.value } : item))} /></label><label><span>{fr ? 'Part (%)' : 'Share (%)'}</span><input type="number" min="0" max="100" value={person.share} onChange={(event) => setCollaborators((items) => items.map((item, i) => i === index ? { ...item, share: event.target.value } : item))} /></label></div>)}</div>
          <button type="button" className="secondary-button" onClick={() => setCollaborators((items) => [...items, { name: '', share: '' }])}><span className="material-icon">person_add</span>{fr ? 'Ajouter un collaborateur' : 'Add collaborator'}</button>
          {contractError && <p className="form-error" role="alert">{contractError}</p>}<button className="primary-button full" type="submit">{fr ? 'Réviser le contrat' : 'Review Contract'}</button>
        </form> : <div className="review-panel"><h3>{contractTrack}</h3><ul>{collaborators.map((person) => <li key={person.name}><span>{person.name}</span><strong>{person.share}%</strong></li>)}</ul><p>{fr ? 'Le service de signature n’est pas connecté; aucun contrat n’a été signé.' : 'The signing service is not connected; no contract has been signed.'}</p><div className="form-actions"><button className="secondary-button" type="button" onClick={() => setContractStep('form')}>{fr ? 'Modifier' : 'Edit'}</button><button className="primary-button" type="button" disabled>{fr ? 'Signature indisponible' : 'Signing Unavailable'}</button></div></div>}
      </DashboardModal>

      <DashboardModal open={activeModal === 'broadcast'} title={fr ? 'Diffusion téléphonique' : 'Phone Broadcast'} eyebrow={t.broadcastFlow} onClose={close} size="wide">
        {broadcastStep === 'form' ? <form className="dashboard-form" onSubmit={submitBroadcast}>
          <label><span>{fr ? 'Destination' : 'Destination'} *</span><input list="broadcast-destinations" value={destinationSearch} onChange={(event) => setDestinationSearch(event.target.value)} placeholder={fr ? 'Rechercher un DJ, une station ou une chaîne' : 'Search a DJ, station, or channel'} /><datalist id="broadcast-destinations">{destinations.map((item) => <option key={item.id} value={item.name}>{item.type} — {item.city}</option>)}</datalist></label>
          {destinationSearch && <div className="search-results" aria-label={fr ? 'Destinations correspondantes' : 'Matching destinations'}>{destinations.filter((item) => `${item.name} ${item.type} ${item.city}`.toLowerCase().includes(destinationSearch.toLowerCase())).map((item) => <button type="button" key={item.id} onClick={() => setDestinationSearch(item.name)}><strong>{item.name}</strong><small>{item.type} • {item.city}</small></button>)}</div>}
          <label><span>{fr ? 'Morceau disponible' : 'Available track'} *</span><input list="broadcast-tracks" value={trackSearch} onChange={(event) => setTrackSearch(event.target.value)} placeholder={fr ? 'Rechercher un morceau' : 'Search for a track'} /><datalist id="broadcast-tracks">{tracks.map((track) => <option key={track} value={track} />)}</datalist></label>
          {broadcastError && <p className="form-error" role="alert">{broadcastError}</p>}<button className="primary-button full" type="submit">{fr ? 'Réviser la diffusion' : 'Review Broadcast'}</button>
        </form> : <div className="review-panel"><h3>{fr ? 'Destination' : 'Destination'}</h3><p><strong>{destination}</strong></p><dl><div><dt>{fr ? 'Morceau' : 'Track'}</dt><dd>{broadcastTrack}</dd></div></dl><p>{fr ? 'Le service de diffusion n’est pas connecté; aucune demande n’a été envoyée.' : 'The broadcast service is not connected; no request has been sent.'}</p><div className="form-actions"><button className="secondary-button" type="button" onClick={() => setBroadcastStep('form')}>{fr ? 'Modifier' : 'Edit'}</button><button className="primary-button" type="button" disabled>{fr ? 'Diffusion indisponible' : 'Broadcast Unavailable'}</button></div></div>}
      </DashboardModal>
    </>
  )
}
