import { useEffect, useMemo, useState } from 'react'
import { useDashboard } from '../dashboardContext'
import { getApiErrorMessage } from '../services/api/client'
import { listBroadcastDestinations, listBroadcastTracks, sendBroadcast } from '../services/api/broadcasts'

export default function PhoneBroadcastPage() {
  const { language } = useDashboard()
  const fr = language === 'fr'
  const [destinations, setDestinations] = useState([])
  const [tracks, setTracks] = useState([])
  const [destinationSearch, setDestinationSearch] = useState('')
  const [trackSearch, setTrackSearch] = useState('')
  const [step, setStep] = useState('form')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [dispatch, setDispatch] = useState(null)
  const [destination, setDestination] = useState(null)
  const [track, setTrack] = useState(null)
  const [note, setNote] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([listBroadcastDestinations(), listBroadcastTracks()])
      .then(([destinationItems, trackItems]) => {
        if (!active) return
        setDestinations(destinationItems)
        setTracks(trackItems)
      })
      .catch((requestError) => {
        if (active) setError(getApiErrorMessage(requestError, 'Could not load broadcast options.'))
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const filteredDestinations = useMemo(() => {
    const query = destinationSearch.toLowerCase()
    return destinations.filter((item) => `${item.label} ${item.type} ${item.city}`.toLowerCase().includes(query))
  }, [destinationSearch, destinations])
  const filteredTracks = useMemo(() => {
    const query = trackSearch.toLowerCase()
    return tracks.filter((item) => `${item.title} ${item.artist_name}`.toLowerCase().includes(query))
  }, [trackSearch, tracks])

  const review = (event) => {
    event.preventDefault()
    setError('')
    const selectedDestination = destinations.find((item) => item.label === destinationSearch.trim())
    const selectedTrack = tracks.find((item) => item.title === trackSearch.trim())
    if (!selectedDestination) {
      setError(fr ? 'Sélectionnez une destination valide.' : 'Select a destination from the API results.')
      return
    }
    if (!selectedTrack) {
      setError(fr ? 'Sélectionnez un morceau disponible.' : 'Select a track registered for broadcast.')
      return
    }
    setDestination(selectedDestination)
    setTrack(selectedTrack)
    setStep('review')
  }

  const submit = async () => {
    setError('')
    setSubmitting(true)
    try {
      const result = await sendBroadcast(track.id, destination.id, note.trim())
      setDispatch(result.dispatches[0])
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Could not submit the broadcast.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="broadcast-page">
      <section className="broadcast-heading"><div><span className="broadcast-eyebrow">CamerHits • {fr ? 'Diffusion API' : 'API Broadcast'}</span><h1>{fr ? 'Diffusion téléphonique' : 'Phone Broadcast'}</h1><p>{fr ? 'Sélectionnez une destination et un morceau associés à votre compte.' : 'Choose an API-registered DJ or broadcaster and a track owned by your account.'}</p></div><span className="demo-tag">API dispatch</span></section>
      <section className="broadcast-panel">
        {loading ? <p role="status">{fr ? 'Chargement des destinations et morceaux…' : 'Loading destinations and tracks…'}</p> : error && step === 'form' && !destinations.length && !tracks.length ? <p className="form-error" role="alert">{error}</p> : dispatch ? (
          <div className="success-panel" role="status"><span className="material-icon">check_circle</span><div><strong>{fr ? 'Demande de diffusion enregistrée' : 'Broadcast dispatch recorded'}</strong><p>{dispatch.track.title} → {dispatch.destination.label} · {dispatch.status}</p><small>{fr ? 'Le backend a enregistré la demande; la livraison externe dépend des services connectés.' : 'The backend recorded this dispatch; external station delivery depends on connected providers.'}</small></div></div>
        ) : step === 'form' ? <form className="dashboard-form" onSubmit={review}>
          <div className="broadcast-search-grid">
            <fieldset><legend>{fr ? 'Destination' : 'Destination'} *</legend><input type="search" value={destinationSearch} onChange={(event) => setDestinationSearch(event.target.value)} placeholder={fr ? 'Rechercher DJ, radio ou TV' : 'Search DJ, radio, or TV'} list="page-destinations" /><datalist id="page-destinations">{destinations.map((item) => <option key={item.id} value={item.label} />)}</datalist><div className="broadcast-list">{filteredDestinations.map((item) => <button type="button" key={item.id} className={destinationSearch === item.label ? 'selected' : ''} onClick={() => setDestinationSearch(item.label)}><span className="material-icon">{item.type === 'dj' ? 'person' : item.medium === 'tv' ? 'tv' : 'radio'}</span><span><strong>{item.label}</strong><small>{item.type} · {item.city}{item.is_verified ? ' · Verified' : ''}</small></span></button>)}</div>{destinations.length === 0 && <small>{fr ? 'Aucune destination disponible.' : 'No eligible destinations are registered yet.'}</small>}</fieldset>
            <fieldset><legend>{fr ? 'Morceau disponible' : 'Available track'} *</legend><input type="search" value={trackSearch} onChange={(event) => setTrackSearch(event.target.value)} placeholder={fr ? 'Rechercher un morceau' : 'Search a track'} list="page-tracks" /><datalist id="page-tracks">{tracks.map((item) => <option key={item.id} value={item.title} />)}</datalist><div className="broadcast-list">{filteredTracks.map((item) => <button type="button" key={item.id} className={trackSearch === item.title ? 'selected' : ''} onClick={() => setTrackSearch(item.title)}><span className="material-icon">music_note</span><span><strong>{item.title}</strong><small>{item.artist_name} · {item.genre}</small></span></button>)}</div>{tracks.length === 0 && <small>{fr ? 'Téléversez un morceau depuis le catalogue pour le rendre disponible.' : 'Upload a song in Catalog to register it for broadcast.'}</small>}</fieldset>
          </div>
          <label><span>{fr ? 'Note facultative' : 'Optional note'}</span><textarea rows="3" maxLength="2000" value={note} onChange={(event) => setNote(event.target.value)} /></label>
          {error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button full" type="submit" disabled={!destinations.length || !tracks.length}>{fr ? 'Vérifier la diffusion' : 'Review Broadcast'}</button>
        </form> : <div className="review-panel"><h2>{fr ? 'Confirmer la demande' : 'Confirm Broadcast Request'}</h2><dl><div><dt>{fr ? 'Destination' : 'Destination'}</dt><dd>{destination.label}<small>{destination.type} · {destination.city}</small></dd></div><div><dt>{fr ? 'Morceau' : 'Track'}</dt><dd>{track.title} · {track.genre}</dd></div>{note && <div><dt>{fr ? 'Note' : 'Note'}</dt><dd>{note}</dd></div>}</dl><p>{fr ? 'La demande sera enregistrée par le backend; cela ne garantit pas la livraison à une station externe.' : 'The backend will record this dispatch; it does not guarantee delivery to an external station.'}</p>{error && <p className="form-error" role="alert">{error}</p>}<div className="form-actions"><button className="secondary-button" type="button" onClick={() => { setStep('form'); setError('') }}>{fr ? 'Modifier' : 'Edit'}</button><button className="primary-button" type="button" onClick={submit} disabled={submitting}>{submitting ? (fr ? 'Envoi…' : 'Sending…') : (fr ? 'Enregistrer la diffusion' : 'Create Dispatch')}</button></div></div>}
      </section>
    </main>
  )
}
