import { useState } from 'react'
import { useDashboard } from '../dashboardContext'

const destinations = [
  { id: 'dj-nzo', name: 'DJ Nzo', type: 'DJ', city: 'Douala' },
  { id: 'hit-radio', name: 'Hit FM Cameroon', type: 'Radio station', city: 'Douala' },
  { id: 'crtv', name: 'CRTV Channel 1', type: 'TV channel', city: 'Yaoundé' },
  { id: 'buea-sound', name: 'Buea Sound Radio', type: 'Radio station', city: 'Buea' },
]
const tracks = ['Midnight Rain', 'Buea Town Vibe', 'Douala Dusk', 'Bamenda Sunrise']

export default function PhoneBroadcastPage() {
  const { language } = useDashboard()
  const fr = language === 'fr'
  const [destinationSearch, setDestinationSearch] = useState('')
  const [trackSearch, setTrackSearch] = useState('')
  const [step, setStep] = useState('form')
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [destination, setDestination] = useState(null)
  const [track, setTrack] = useState('')

  const filteredDestinations = destinations.filter((item) => `${item.name} ${item.type} ${item.city}`.toLowerCase().includes(destinationSearch.toLowerCase()))
  const filteredTracks = tracks.filter((item) => item.toLowerCase().includes(trackSearch.toLowerCase()))

  const review = (event) => {
    event.preventDefault()
    setError('')
    const selectedDestination = destinations.find((item) => item.name.toLowerCase() === destinationSearch.trim().toLowerCase())
    const selectedTrack = tracks.find((item) => item.toLowerCase() === trackSearch.trim().toLowerCase())
    if (!selectedDestination) return setError(fr ? 'Sélectionnez une destination valide.' : 'Select a valid destination.')
    if (!selectedTrack) return setError(fr ? 'Sélectionnez un morceau valide.' : 'Select a valid track.')
    setDestination(selectedDestination)
    setTrack(selectedTrack)
    setStep('review')
  }

  return (
    <main className="broadcast-page">
      <section className="broadcast-heading"><div><span className="broadcast-eyebrow">CamerHits • {fr ? 'Démonstration' : 'Demo'}</span><h1>{fr ? 'Diffusion téléphonique' : 'Phone Broadcast'}</h1><p>{fr ? 'Choisissez une destination exemple et un morceau disponible.' : 'Choose a sample destination and an available track.'}</p></div><span className="demo-tag">{fr ? 'Aucun envoi réel' : 'No real broadcast'}</span></section>
      <section className="broadcast-panel">
        {submitted ? <div className="success-panel" role="status"><span className="material-icon">check_circle</span><div><strong>{fr ? 'Demande démo soumise' : 'Demo broadcast request submitted'}</strong><p>{fr ? 'Aucune diffusion réelle n’a été envoyée.' : 'No real broadcast was sent.'}</p></div></div> : step === 'form' ? <form className="dashboard-form" onSubmit={review}>
          <div className="broadcast-search-grid">
            <fieldset><legend>{fr ? 'Destination' : 'Destination'} *</legend><input type="search" value={destinationSearch} onChange={(event) => setDestinationSearch(event.target.value)} placeholder={fr ? 'Rechercher DJ, radio ou TV' : 'Search DJ, radio, or TV'} list="page-destinations" /><datalist id="page-destinations">{destinations.map((item) => <option key={item.id} value={item.name}>{item.type} — {item.city}</option>)}</datalist><div className="broadcast-list">{filteredDestinations.map((item) => <button type="button" key={item.id} className={destinationSearch === item.name ? 'selected' : ''} onClick={() => setDestinationSearch(item.name)}><span className="material-icon">{item.type === 'DJ' ? 'person' : item.type.includes('TV') ? 'tv' : 'radio'}</span><span><strong>{item.name}</strong><small>{item.type} • {item.city}</small></span></button>)}</div></fieldset>
            <fieldset><legend>{fr ? 'Morceau disponible' : 'Available track'} *</legend><input type="search" value={trackSearch} onChange={(event) => setTrackSearch(event.target.value)} placeholder={fr ? 'Rechercher un morceau' : 'Search a track'} list="page-tracks" /><datalist id="page-tracks">{tracks.map((item) => <option key={item} value={item} />)}</datalist><div className="broadcast-list">{filteredTracks.map((item) => <button type="button" key={item} className={trackSearch === item ? 'selected' : ''} onClick={() => setTrackSearch(item)}><span className="material-icon">music_note</span><span><strong>{item}</strong><small>{fr ? 'Morceau disponible' : 'Available track'}</small></span></button>)}</div></fieldset>
          </div>
          {error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button full" type="submit">{fr ? 'Réviser la diffusion' : 'Review Broadcast'}</button>
        </form> : <div className="review-panel"><span className="demo-banner">{fr ? 'Confirmation démo — aucune diffusion réelle' : 'Demo confirmation — no real broadcast'}</span><h2>{fr ? 'Confirmer la demande' : 'Confirm Broadcast Request'}</h2><dl><div><dt>{fr ? 'Destination' : 'Destination'}</dt><dd>{destination.name}<small>{destination.type} • {destination.city}</small></dd></div><div><dt>{fr ? 'Morceau' : 'Track'}</dt><dd>{track}</dd></div></dl><div className="form-actions"><button className="secondary-button" type="button" onClick={() => setStep('form')}>{fr ? 'Modifier' : 'Edit'}</button><button className="primary-button" type="button" onClick={() => setSubmitted(true)}>{fr ? 'Soumettre la demande démo' : 'Submit Demo Request'}</button></div></div>}
      </section>
    </main>
  )
}
