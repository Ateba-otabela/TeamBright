import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import DashboardModal from '../components/DashboardModal'
import { useDashboard } from '../dashboardContext'

const initialSongs = [
  { id: 'bamenda-sunrise', title: 'Bamenda Sunrise', status: 'draft', date: 'Nov 22, 2026', meta: 'Afropop / Makossa • 118 BPM • 3:06 • Pidgin / FR • Chorus 16s', genre: 'Afropop / Makossa', language: 'Pidgin / FR', bpm: '118', duration: '3:06', chorus: '16', price: '500', sales: 'Pre-release', score: '--', action: 'Finish & Publish', actionTo: '/catalog-vault', cover: '/covers/bamenda-sunrise.jpg' },
  { id: 'midnight-rain', title: 'Midnight Rain', status: 'live', date: 'Nov 08, 2026', flag: 'SLOW_HOOK', meta: 'Afro-Soul • 96 BPM • 3:48 • EN / FR • Chorus 44s', genre: 'Afro-Soul', language: 'EN / FR', bpm: '96', duration: '3:48', chorus: '44', price: '1,000', sales: '122 sales • 171 spins', score: '41.2', action: 'Inspect AI', actionTo: '/ai-advisor', cover: '/covers/midnight-rain.jpg' },
  { id: 'buea-town-vibe', title: 'Buea Town Vibe', status: 'live', date: 'Oct 19, 2026', meta: 'Afropop • 114 BPM • 3:12 • Pidgin / EN • Chorus 18s', genre: 'Afropop', language: 'Pidgin / EN', bpm: '114', duration: '3:12', chorus: '18', price: '500', sales: '218 sales • 450 spins', score: '86.4', action: 'View Splits', actionTo: '/split-contracts', cover: '/covers/buea-town-vibe.jpg' },
  { id: 'douala-dusk', title: 'Douala Dusk', status: 'live', date: 'Sep 28, 2026', meta: 'Bikutsi Fusion • 122 BPM • 2:54 • FR / Ewondo • Chorus 19s', genre: 'Bikutsi Fusion', language: 'FR / Ewondo', bpm: '122', duration: '2:54', chorus: '19', price: '500', sales: '164 sales • 310 spins', score: '78.9', action: 'View Splits', actionTo: '/split-contracts', cover: '/covers/douala-dusk.jpg' },
  { id: 'limbe-breeze', title: 'Limbe Breeze (Acoustic)', status: 'draft', date: 'Sep 11, 2026', meta: 'Afro-Acoustic • 88 BPM • 3:30 • EN • Chorus 21s', genre: 'Afro-Acoustic', language: 'EN', bpm: '88', duration: '3:30', chorus: '21', price: '500', sales: 'Pre-release', score: '--', action: 'Edit Draft', actionTo: '/catalog-vault', cover: '/covers/limbe-breeze.jpg' },
]

const emptyDraft = { title: '', genre: '', language: '', bpm: '', duration: '', chorus: '16', price: '500', audioName: '', coverData: '' }

function SongRow({ song, onEdit, onPublish }) {
  const scoreClass = song.score === '--' ? 'catalog-score empty' : 'catalog-score'
  const actionClass = song.status === 'draft' ? 'catalog-song-action primary' : song.action === 'Inspect AI' ? 'catalog-song-action accent' : 'catalog-song-action'

  return (
    <article className={`catalog-song-row${song.flag ? ' flagged' : ''}`}>
      <div className="catalog-song-main">
        <img className="catalog-song-cover" src={song.cover} alt={`${song.title} cover artwork`} />
        <div className="catalog-song-details">
          <div className="catalog-song-title-line">
            <h2>{song.title}</h2>
            <span className={`catalog-status ${song.status}`}>{song.status === 'live' ? 'Live' : 'Draft'}</span>
            {song.flag && <span className="catalog-song-flags">{song.flag}</span>}
            <time>{song.date}</time>
          </div>
          <p>{song.meta}</p>
        </div>
      </div>
      <div className="catalog-song-stats">
        <div><small>Price</small><strong className={song.status === 'live' ? 'catalog-live-value' : ''}>{song.price} XAF</strong></div>
        <div><small>Sales / Spins</small><strong className={song.title === 'Buea Town Vibe' ? 'catalog-live-value' : ''}>{song.sales}</strong></div>
        <div className="catalog-song-actions">
          <span className={scoreClass}>{song.score}</span>
          {song.status === 'draft' ? (
            <div className="draft-actions">
              <button type="button" className="catalog-song-action" onClick={() => onEdit(song)}>Edit Draft</button>
              <button type="button" className={actionClass} onClick={() => onPublish(song)}>Finish &amp; Publish</button>
            </div>
          ) : song.actionTo ? <Link className={actionClass} to={song.actionTo}>{song.action}</Link> : null}
        </div>
      </div>
    </article>
  )
}

export default function CatalogPage() {
  const { language } = useDashboard()
  const fr = language === 'fr'
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [songs, setSongs] = useState(() => {
    try { return JSON.parse(localStorage.getItem('camerhits-catalog-songs')) || initialSongs } catch { return initialSongs }
  })
  const [modal, setModal] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [draft, setDraft] = useState(emptyDraft)
  const [error, setError] = useState('')
  const [publishTarget, setPublishTarget] = useState(null)

  useEffect(() => { localStorage.setItem('camerhits-catalog-songs', JSON.stringify(songs)) }, [songs])

  const visibleSongs = useMemo(() => songs.filter((song) => {
    const matchesStatus = filter === 'all' || song.status === filter
    const searchable = `${song.title} ${song.meta}`.toLowerCase()
    return matchesStatus && searchable.includes(search.trim().toLowerCase())
  }), [filter, search, songs])

  const openAdd = () => { setEditingId(null); setDraft(emptyDraft); setError(''); setModal('form') }
  const openEdit = (song) => { setEditingId(song.id); setDraft({ title: song.title, genre: song.genre || '', language: song.language || '', bpm: song.bpm || '', duration: song.duration || '', chorus: song.chorus || '', price: song.price?.replace(' XAF','') || '', audioName: song.audioName || '', coverData: song.cover || '' }); setError(''); setModal('form') }
  const openPublish = (song) => { setPublishTarget(song); setModal('publish') }

  const onAudio = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (!/\.(mp3|wav|m4a|aac|flac)$/i.test(file.name)) { setError(fr ? 'Format audio accepté : MP3, WAV, M4A, AAC ou FLAC.' : 'Accepted audio: MP3, WAV, M4A, AAC, or FLAC.') ; return }
    setDraft((value) => ({ ...value, audioName: file.name }))
    setError('')
  }

  const onCover = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) { setError(fr ? 'Format de couverture accepté : JPG, PNG ou WebP.' : 'Accepted cover: JPG, PNG, or WebP.') ; return }
    const reader = new FileReader()
    reader.onload = () => { setDraft((value) => ({ ...value, coverData: String(reader.result) })); setError('') }
    reader.readAsDataURL(file)
  }

  const saveDraft = (event) => {
    event.preventDefault()
    if (!draft.title.trim()) return setError(fr ? 'Le titre est obligatoire.' : 'Title is required.')
    if (!draft.genre.trim()) return setError(fr ? 'Le genre est obligatoire.' : 'Genre is required.')
    if (!draft.language.trim()) return setError(fr ? 'La langue est obligatoire.' : 'Language is required.')
    if (!draft.bpm || Number(draft.bpm) <= 0) return setError(fr ? 'Le BPM doit être supérieur à zéro.' : 'BPM must be greater than zero.')
    if (!draft.duration.trim()) return setError(fr ? 'La durée est obligatoire.' : 'Duration is required.')
    if (!draft.price || Number(draft.price) <= 0) return setError(fr ? 'Le prix doit être supérieur à zéro.' : 'Price must be greater than zero.')
    if (!editingId && !draft.audioName) return setError(fr ? 'Sélectionnez un fichier audio.' : 'Select an audio file.')
    if (!editingId && !draft.coverData) return setError(fr ? 'Sélectionnez une image de couverture.' : 'Select a cover image.')

    const meta = `${draft.genre} • ${draft.bpm} BPM • ${draft.duration} • ${draft.language} • Chorus ${draft.chorus || '16'}s`
    const now = new Date().toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
    const cover = draft.coverData || '/covers/bamenda-sunrise.jpg'

    if (editingId) {
      setSongs((items) => items.map((item) => item.id === editingId ? { ...item, title: draft.title.trim(), genre: draft.genre.trim(), language: draft.language.trim(), bpm: draft.bpm, duration: draft.duration, chorus: draft.chorus, price: draft.price, audioName: draft.audioName, cover, meta } : item))
    } else {
      setSongs((items) => [{ id: `draft-${Date.now()}`, title: draft.title.trim(), status: 'draft', date: now, genre: draft.genre.trim(), language: draft.language.trim(), bpm: draft.bpm, duration: draft.duration, chorus: draft.chorus, price: draft.price, sales: 'Pre-release', score: '--', action: 'Finish & Publish', meta, audioName: draft.audioName, cover }, ...items])
    }
    setModal(null)
  }

  const confirmPublish = () => {
    if (!publishTarget) return
    setSongs((items) => items.map((item) => item.id === publishTarget.id ? { ...item, status: 'live', sales: '0 sales • 0 spins', score: '--', action: 'View Splits', actionTo: '/split-contracts', flag: undefined } : item))
    setModal(null)
    setPublishTarget(null)
  }

  return (
    <main className="catalog-page">
      <section className="catalog-title-row">
        <div><h1>{fr ? 'Chansons & sorties directes' : 'Recent Songs & Direct Releases'}</h1><p>{fr ? 'Gérez les pistes, les distributions et les scores' : 'All 5 recent tracks by Kamga Beats — track Hit Scores, direct B2C XAF sales, and verified DJ spins.'}</p></div>
        <button className="catalog-add-button" type="button" onClick={openAdd}><span className="material-icon">add</span><span>{fr ? 'Ajouter un morceau' : 'Add Song'}</span></button>
      </section>

      <section className="catalog-controls">
        <div className="catalog-filter-tabs" aria-label="Filter songs">
          {[['all', fr ? `Tout (${songs.length})` : `All Songs (${songs.length})`], ['live', fr ? `En ligne (${songs.filter(s => s.status === 'live').length})` : `Live (${songs.filter(s => s.status === 'live').length})`], ['draft', fr ? `Brouillons (${songs.filter(s => s.status === 'draft').length})` : `Drafts (${songs.filter(s => s.status === 'draft').length})`]].map(([value, label]) => <button key={value} type="button" className={filter === value ? 'active' : ''} onClick={() => setFilter(value)}>{label}</button>)}
        </div>
        <label className="catalog-search"><span className="material-icon">search</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={fr ? 'Rechercher titre, genre ou langue...' : 'Search title, genre, or language...'} /></label>
      </section>

      <section className="catalog-song-list" aria-label="Recent songs">
        {visibleSongs.map((song) => <SongRow key={song.id} song={song} onEdit={openEdit} onPublish={openPublish} />)}
        {visibleSongs.length === 0 && <div className="catalog-empty">{fr ? 'Aucun morceau ne correspond à votre recherche.' : 'No songs match your search.'}</div>}
      </section>

      <DashboardModal open={modal === 'form'} title={editingId ? (fr ? 'Modifier le brouillon' : 'Edit Draft') : (fr ? 'Ajouter un morceau' : 'Add Song')} eyebrow={fr ? 'Démo locale — aucun serveur configuré' : 'Local demo — no server configured'} onClose={() => setModal(null)} size="wide">
        <form className="dashboard-form catalog-track-form" onSubmit={saveDraft}>
          <div className="form-grid">
            <label><span>{fr ? 'Titre' : 'Title'} *</span><input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} required /></label>
            <label><span>{fr ? 'Genre' : 'Genre'} *</span><input value={draft.genre} onChange={(event) => setDraft({ ...draft, genre: event.target.value })} required /></label>
          </div>
          <div className="form-grid">
            <label><span>{fr ? 'Langue' : 'Language'} *</span><input value={draft.language} onChange={(event) => setDraft({ ...draft, language: event.target.value })} required /></label>
            <label><span>BPM *</span><input type="number" min="1" value={draft.bpm} onChange={(event) => setDraft({ ...draft, bpm: event.target.value })} required /></label>
          </div>
          <div className="form-grid">
            <label><span>{fr ? 'Durée' : 'Duration'} *</span><input value={draft.duration} onChange={(event) => setDraft({ ...draft, duration: event.target.value })} placeholder="3:30" required /></label>
            <label><span>{fr ? 'Début du refrain (secondes)' : 'Chorus timing (seconds)'} *</span><input type="number" min="0" value={draft.chorus} onChange={(event) => setDraft({ ...draft, chorus: event.target.value })} required /></label>
          </div>
          <label><span>{fr ? 'Prix (XAF)' : 'Price (XAF)'} *</span><input type="number" min="1" value={draft.price} onChange={(event) => setDraft({ ...draft, price: event.target.value })} required /></label>
          <label><span>{fr ? 'Fichier audio' : 'Audio file'} {!editingId && '*'}</span><input type="file" accept=".mp3,.wav,.m4a,.aac,.flac,audio/*" onChange={onAudio} />{draft.audioName && <small>{draft.audioName}</small>}</label>
          <label><span>{fr ? 'Image de couverture' : 'Cover image'}</span><input type="file" accept="image/jpeg,image/png,image/webp" onChange={onCover} /></label>
          {draft.coverData && <img className="catalog-form-preview" src={draft.coverData} alt={fr ? 'Aperçu de la couverture' : 'Cover preview'} />}
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button full" type="submit">{editingId ? (fr ? 'Enregistrer le brouillon' : 'Save Draft') : (fr ? 'Ajouter comme brouillon' : 'Add as Draft')}</button>
        </form>
      </DashboardModal>

      <DashboardModal open={modal === 'publish'} title={fr ? 'Réviser la publication démo' : 'Review Demo Publication'} eyebrow={fr ? 'Aucun service de publication réel configuré' : 'No real publishing service configured'} onClose={() => setModal(null)}>
        {publishTarget && <div className="review-panel"><h3>{publishTarget.title}</h3><dl><div><dt>{fr ? 'Genre' : 'Genre'}</dt><dd>{publishTarget.genre}</dd></div><div><dt>{fr ? 'Langue' : 'Language'}</dt><dd>{publishTarget.language}</dd></div><div><dt>BPM</dt><dd>{publishTarget.bpm}</dd></div><div><dt>{fr ? 'Durée' : 'Duration'}</dt><dd>{publishTarget.duration}</dd></div><div><dt>{fr ? 'Refrain' : 'Chorus'}</dt><dd>{publishTarget.chorus}s</dd></div><div><dt>{fr ? 'Prix' : 'Price'}</dt><dd>{publishTarget.price} XAF</dd></div></dl><p>{fr ? 'Confirmation démo : aucun téléchargement ou publication en temps réel n’aura lieu.' : 'Demo confirmation: no real upload or live publication will occur.'}</p><div className="form-actions"><button className="secondary-button" type="button" onClick={() => setModal(null)}>{fr ? 'Annuler' : 'Cancel'}</button><button className="primary-button" type="button" onClick={confirmPublish}>{fr ? 'Publier en démo' : 'Publish in Demo'}</button></div></div>}
      </DashboardModal>
    </main>
  )
}
