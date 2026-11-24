import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import DashboardModal from '../components/DashboardModal'
import { useAuth } from '../authContext'
import { useDashboard } from '../dashboardContext'
import { getApiAssetUrl, getApiErrorMessage } from '../services/api/client'
import { listMySongs, listRecentSongs, registerBroadcastTrack, uploadSong } from '../services/api/songs'

const MAX_SONG_BYTES = 30 * 1024 * 1024
const genres = ['Afrobeats', 'Afropop', 'Makossa', 'Bikutsi', 'Afro-Soul', 'Gospel', 'Hip-Hop', 'Reggae', 'Other']

function formatSong(song) {
  const date = song.created_at
    ? new Date(song.created_at).toLocaleDateString()
    : ''
  return {
    ...song,
    status: 'live',
    date,
    meta: `${song.artist_name} · ${(song.audio_size / (1024 * 1024)).toFixed(1)} MB`,
    price: '—',
    sales: '—',
    score: '—',
    action: 'Inspect AI',
    actionTo: '/ai-advisor',
  }
}

function SongRow({ song }) {
  return (
    <article className="catalog-song-row">
      <div className="catalog-song-main">
        <div className="catalog-song-cover catalog-song-placeholder" aria-hidden="true">
          <span className="material-icon">music_note</span>
        </div>
        <div className="catalog-song-details">
          <div className="catalog-song-title-line">
            <h2>{song.title}</h2>
            <span className="catalog-status live">Available</span>
            <time>{song.date}</time>
          </div>
          <p>{song.meta}</p>
          <audio className="catalog-song-audio" controls preload="none" src={getApiAssetUrl(song.audio_url)}>
            Your browser does not support audio playback.
          </audio>
        </div>
      </div>
      <div className="catalog-song-stats">
        <div><small>Price</small><strong>{song.price}</strong></div>
        <div><small>Sales</small><strong>{song.sales}</strong></div>
        <div className="catalog-song-actions">
          <span className="catalog-score empty">{song.score}</span>
          <Link className="catalog-song-action accent" to={song.actionTo}>{song.action}</Link>
        </div>
      </div>
    </article>
  )
}

export default function CatalogPage() {
  const { user } = useAuth()
  const { language, refreshOverview } = useDashboard()
  const fr = language === 'fr'
  const [songs, setSongs] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [genre, setGenre] = useState('')
  const [audioFile, setAudioFile] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadSongs = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const items = user?.role === 'artist' ? await listMySongs() : await listRecentSongs()
      setSongs(items.map(formatSong))
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Could not load songs.'))
    } finally {
      setLoading(false)
    }
  }, [fr, user?.id, user?.role])

  useEffect(() => { loadSongs() }, [loadSongs])

  const visibleSongs = useMemo(() => {
    const query = search.trim().toLowerCase()
    return songs.filter((song) => `${song.title} ${song.artist_name}`.toLowerCase().includes(query))
  }, [search, songs])

  const submitUpload = async (event) => {
    event.preventDefault()
    setError('')
    setNotice('')
    if (!audioFile) {
      setError(fr ? 'Sélectionnez un fichier MP3.' : 'Select an MP3 file.')
      return
    }
    if (!audioFile.name.toLowerCase().endsWith('.mp3') || audioFile.size > MAX_SONG_BYTES) {
      setError(fr ? 'Le fichier doit être un MP3 de 30 Mo maximum.' : 'Choose an MP3 file no larger than 30 MB.')
      return
    }

    setSaving(true)
    let registrationError = ''
    try {
      const uploadedSong = await uploadSong(title.trim(), audioFile)
      try {
        await registerBroadcastTrack(uploadedSong, genre.trim() || 'unspecified')
        setNotice(fr ? 'Morceau téléversé et ajouté aux diffusions.' : 'Song uploaded and made available for broadcasts.')
      } catch (broadcastError) {
        setNotice(fr ? 'Morceau téléversé, mais son inscription aux diffusions a échoué.' : 'Song uploaded, but it could not be registered for broadcasts.')
        registrationError = getApiErrorMessage(broadcastError)
      }
      setTitle('')
      setGenre('')
      setAudioFile(null)
      setModalOpen(false)
      await loadSongs()
      await refreshOverview()
      if (registrationError) setError(registrationError)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Could not upload this song.'))
    } finally {
      setSaving(false)
    }
  }

  const canUpload = user?.role === 'artist'

  return (
    <main className="catalog-page">
      <section className="catalog-title-row">
        <div><h1>{fr ? 'Chansons & sorties directes' : 'Songs & Direct Releases'}</h1><p>{fr ? 'Catalogue chargé depuis le serveur CamerHits.' : 'Songs and audio uploads provided by the CamerHits API.'}</p></div>
        {canUpload && <button className="catalog-add-button" type="button" onClick={() => { setError(''); setNotice(''); setModalOpen(true) }}><span className="material-icon">add</span><span>{fr ? 'Téléverser un morceau' : 'Upload Song'}</span></button>}
      </section>

      <section className="catalog-controls">
        <div className="catalog-filter-tabs"><span>{songs.length} {fr ? 'morceaux' : 'songs'}</span></div>
        <label className="catalog-search"><span className="material-icon">search</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={fr ? 'Rechercher par titre ou artiste...' : 'Search by title or artist...'} /></label>
      </section>

      {error && !modalOpen && <p className="form-error" role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <section className="catalog-song-list" aria-label="Songs">
        {loading && <p role="status">{fr ? 'Chargement des morceaux…' : 'Loading songs…'}</p>}
        {!loading && visibleSongs.map((song) => <SongRow key={song.id} song={song} />)}
        {!loading && visibleSongs.length === 0 && <div className="catalog-empty">{error ? '' : fr ? 'Aucun morceau disponible.' : 'No songs available yet.'}</div>}
      </section>

      <DashboardModal open={modalOpen} title={fr ? 'Téléverser un morceau' : 'Upload a Song'} eyebrow={fr ? 'MP3 · 30 Mo maximum' : 'MP3 · 30 MB maximum'} onClose={() => setModalOpen(false)} size="wide">
        <form className="dashboard-form catalog-track-form" onSubmit={submitUpload}>
          <label><span>{fr ? 'Titre' : 'Title'} *</span><input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} required /></label>
          <label><span>{fr ? 'Genre (pour les diffusions)' : 'Genre (for broadcasts)'} *</span><select value={genre} onChange={(event) => setGenre(event.target.value)} required><option value="" disabled>{fr ? 'Choisir un genre' : 'Select a genre'}</option>{genres.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label><span>{fr ? 'Fichier audio MP3' : 'MP3 audio file'} *</span><input type="file" accept=".mp3,audio/mpeg" onChange={(event) => setAudioFile(event.target.files?.[0] || null)} required /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button full" type="submit" disabled={saving}>{saving ? (fr ? 'Téléversement…' : 'Uploading…') : (fr ? 'Téléverser' : 'Upload Song')}</button>
        </form>
      </DashboardModal>
    </main>
  )
}
