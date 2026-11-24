import { Link } from 'react-router-dom'
import { useState } from 'react'
import './LandingPage.css'

const playlists = [
  { title: 'Daily Mix 1', detail: 'Buea & Douala top rotation', image: 'https://lh3.googleusercontent.com/aida/ALJJyrDFJUKrXMrZv0lavjm1U75r0QKo4mv5aD6ZkEK4OStqv-TqFFF52xaDdJ8ntrGAt4l3RwB7f7Xu8hvz91bbRHDqg7mxpXu41SUSwAjkD9p9hYJUVAKXjsWgp55q60jg-NIrjtuKc3z7hF9SeSem29g10GRx9VaOFifAkmWVmhZc-BaMkKu9RfmuBX3-iVjEkSxqgimjKTS3_9MrJyu3F88dU-KOhdICJRSpSQBDnSjBwwweyJ2dac4e' },
  { title: 'Limbe Chill Hits', detail: 'Acoustic & sunset vibes', image: 'https://lh3.googleusercontent.com/aida/ALJJyrD4h1Lsf3luAvnWeSZRg4eCa27Yy-22rswKE09ejyJgLS4Xm8OyL9X7ZpiLGItoty5LjgyBhxjfH9lo9FHVsgKbGmwr-Fd-gFvMEywGDvKtYzgCQuXD-n_FtCbP9NF9voH7e6CVlkF-jK6egj77sErPU-v2PwDEYfcHoN_YR560VpTtmk1vgB0h8y1o8nJQypgjUyebyMIYt7ksIULZMY-Lpn001woQYGc8r4fbvHeulyESPA2Sek4APyo' },
  { title: 'Bikutsi & Energy', detail: 'High-tempo club & gym hits', image: 'https://lh3.googleusercontent.com/aida/ALJJyrBcLluxky3vYpEFJxASLaOJ7d6o1XQ5HKvwkJxeN5GgzeGSjkB7jp2V-CQCMMDbnt2WomVr6CADV0GB_6pUVr-FM_vYRYZ64wXSLgjmSpm2zOKoPtWQtsoHCsJq8zGwtqFZ2oJ43Nmke8fnRCP-hgkzAoD0c4F5XWp1hig301lTyAbcxWLfotacywp5ex80wJJD9HC7jE-uPcQJYlF-WhDZCXjh2EkNJl5hFL3u_oqBT1jT7_a6eiONwXnvUA' },
  { title: 'Douala Late Night', detail: 'Afro-fusion & midnight sets', image: 'https://lh3.googleusercontent.com/aida/ALJJyrBY76wK5k36du0ggrKx4u_FuJ2wXJQsSbs01WsDuqle6NuC0xrPFYxwSazBtk8rqpbEofSd4JZAQEZgCUDK81db48VVoxzs3e8OlK4M-Rf2DoAKB0Z5JZwDCj4MDSrXDR5FtBHUqWX_QtLzanG51J4UkvRMdc3gVdtpfSYOp2bZBqOeXSOPwod2bxXm8RMArRpxsCdmyKAZCCq9E2t3z1aWh-ojEN-yafc2aH_9EZZx1yp3YYXv_Zpp_b9wmA' },
]

const events = [
  { title: 'CIMFEST 2026 Live', date: 'Dec 18 · Buea', place: 'Molyko Omnisports Stadium · Kamga Beats, Locko & DJ Mapoka', price: '2,500 XAF', image: '/assets/cimfest.avif' },
  { title: 'Douala Afrobeats Night', date: 'Dec 24 · Douala', place: 'Canal Olympia Bessengué · Live DJ Showcase & VIP Tables', price: '5,000 XAF', image: '/assets/douala.jpeg' },
  { title: 'Limbe Beach Soundwave', date: 'Jan 03 · Limbe', place: 'Down Beach Stage · Sunset Acoustic & Makossa Live', price: '3,000 XAF', image: 'https://lh3.googleusercontent.com/aida/ALJJyrD4h1Lsf3luAvnWeSZRg4eCa27Yy-22rswKE09ejyJgLS4Xm8OyL9X7ZpiLGItoty5LjgyBhxjfH9lo9FHVsgKbGmwr-Fd-gFvMEywGDvKtYzgCQuXD-n_FtCbP9NF9voH7e6CVlkF-jK6egj77sErPU-v2PwDEYfcHoN_YR560VpTtmk1vgB0h8y1o8nJQypgjUyebyMIYt7ksIULZMY-Lpn001woQYGc8r4fbvHeulyESPA2Sek4APyo' },
]

const channels = [
  ['CRTV', 'CRTV Music', 'Tam-Tam Weekend Top 10', 'ON AIR', '/assets/crtv.png'],
  ['C2', 'Canal 2 Musique', 'Urban Cameroon Countdown', 'ON AIR', '/assets/canal2.jpeg'],
  ['EQX', 'Equinoxe TV', 'Douala Studio Sessions', 'HD', '/assets/equinox.jpeg'],
  ['STV', 'STV Cameroon', 'Midnight Video Mix', 'HD', '/assets/stv.jpeg'],
]

const djs = [
  ['DJ Mapoka', 'Douala · Club & Radio', '142 Spins'],
  ['DJ Labastille', 'Yaoundé · Bikutsi Mix', '118 Spins'],
  ['DJ Kero', 'Buea · Campus & Live', '96 Spins'],
  ['DJ Pazzo', 'Limbe · Beach & Afropop', '84 Spins'],
]

const featuredImage = 'https://lh3.googleusercontent.com/aida/ALJJyrCYDKMeBD4TW81j6IFqTNsc81PDGwVFkWMUCufl7GOguiuan-ATYFusSFPLqPixyKXO0MSjoGeRB4hK3rIJ1Zq58YPyTOQ83qyGRQRkXHdsYjROYo7YtOJaajUOZw_VM3RJ8droS5TDa3rdd3w3U-hFJy7p0o7FFjR6o8L_hhAQdYtH3cv3jFxMC5sFWgpN67wxgJyd7ZmavlE_TMBajjhkdcZfea4ZReKPYO8TuRW7Hf1DfOXOugpPRNdkldPG'

function SectionHeading({ title, detail, action, href = '/login?mode=register' }) {
  return (
    <div className="landing-section-heading">
      <div><h2>{title}</h2><p>{detail}</p></div>
      <Link to={href}>{action} <span aria-hidden="true">→</span></Link>
    </div>
  )
}

export default function LandingPage() {
  const [selectedTrack, setSelectedTrack] = useState({ title: 'Buea Town Vibe', artist: 'Kamga Beats' })
  const [playing, setPlaying] = useState(false)

  const selectTrack = (title, artist = 'Kamga Beats') => {
    setSelectedTrack({ title, artist })
    setPlaying(true)
  }

  return (
    <div className="landing-page">
      <header className="landing-header">
        <div className="landing-header-inner">
          <a className="landing-brand" href="#top"><span className="landing-brand-icon material-icon" aria-hidden="true">graphic_eq</span><strong>CamerHits</strong></a>
          <nav aria-label="Landing sections">
            <a href="#streaming">Streaming</a><a href="#events">Events</a><a href="#tv-channels">TV Channels</a><a href="#djs">DJs</a>
          </nav>
          <div className="landing-header-actions">
            <Link className="landing-button landing-button-muted" to="/login">Sign In</Link>
            <Link className="landing-button landing-button-primary" to="/login?mode=register">Register</Link>
          </div>
        </div>
      </header>

      <main className="landing-main" id="top">
        <section className="landing-hero" id="streaming">
          <div className="landing-hero-copy">
            <span className="landing-eyebrow"><i />Direct Music Streaming · Events · TV · DJs</span>
            <h1>Stream Cameroon’s Sound. Direct to Artists &amp; Fans.</h1>
            <p>Discover trending Afrobeats, Makossa, and Bikutsi tracks, grab instant MTN MoMo event tickets, tune into live Cameroonian TV music shows, and connect straight with club DJs—with zero middlemen.</p>
            <div className="landing-hero-actions">
              <Link className="landing-button landing-button-primary" to="/login?mode=register">Create Free Account <span aria-hidden="true">→</span></Link>
              <Link className="landing-button landing-button-muted" to="/login">Sign In</Link>
              <Link className="landing-text-link" to="/login"><span className="material-icon" aria-hidden="true">play_circle</span> Open Player</Link>
            </div>
            <div className="landing-stats">
              <div><strong>12,400+</strong><span>Cameroonian Tracks</span></div>
              <div><strong>0 XAF</strong><span>Manager Cut</span></div>
              <div><strong>24/7</strong><span>TV &amp; DJ Broadcasts</span></div>
            </div>
          </div>
          <div className="landing-player">
            <div className="landing-featured" style={{ backgroundImage: `linear-gradient(90deg, #0b0d18 0%, rgba(11,13,24,.82) 52%, transparent 100%), url("${featuredImage}")` }}>
              <div className="landing-featured-copy">
                <span className="landing-pill">Featured Drop</span>
                <h2>Discover New Music</h2>
                <p>Fresh Cameroonian hits picked for you</p>
                <button className="landing-button landing-button-primary landing-button-small" type="button" onClick={() => selectTrack('Buea Town Vibe')}>Play Now</button>
              </div>
            </div>
            <div className="landing-mixes">
              {playlists.map((playlist) => (
                <button className="landing-mix" type="button" key={playlist.title} onClick={() => selectTrack(playlist.title)} style={{ backgroundImage: `linear-gradient(180deg, rgba(11,13,24,.38), rgba(11,13,24,.9)), url("${playlist.image}")` }}>
                  <span><strong>{playlist.title}</strong><small>{playlist.detail}</small></span><i className="material-icon" aria-hidden="true">play_arrow</i>
                </button>
              ))}
            </div>
            <div className="landing-now-playing">
              <span className="landing-album-art material-icon" aria-hidden="true">graphic_eq</span>
              <span className="landing-track"><strong>{selectedTrack.title}</strong><small>{selectedTrack.artist} · CamerHits Radio</small></span>
              <span className="landing-track-time">1:42 / 3:36</span>
              <button type="button" aria-label={playing ? 'Pause preview' : 'Play preview'} onClick={() => setPlaying((current) => !current)} className="landing-play-toggle material-icon">{playing ? 'pause' : 'play_arrow'}</button>
            </div>
          </div>
        </section>

        <section className="landing-section" id="events">
          <SectionHeading title="Upcoming Events & Live Concerts" detail="Verified QR tickets and local distributor booths across Cameroon." action="All Events" />
          <div className="landing-event-grid">
            {events.map((event) => (
              <article className="landing-event-card" key={event.title}>
                <div className="landing-event-image" style={{ backgroundImage: `url("${event.image}")` }}><span>{event.date}</span></div>
                <div className="landing-event-info"><h3>{event.title}</h3><p>{event.place}</p></div>
                <div className="landing-event-footer"><strong>{event.price}</strong><Link to="/login?mode=register">Buy Ticket</Link></div>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section" id="tv-channels">
          <SectionHeading title="TV Channels & Live Music Broadcasts" detail="Watch Cameroonian music television networks and track verified airplay." action="Pitch to TV" />
          <div className="landing-channel-grid">
            {channels.map(([initials, name, show, status, image]) => (
              <article className="landing-channel-card" key={name}>
                <div className="landing-channel-top"><span className="landing-channel-logo"><img src={image} alt={`${name} logo`} /><span className="landing-channel-initials">{initials}</span></span><span className="landing-live"><i />{status}</span></div>
                <div><h3>{name}</h3><p>Now Playing: {show}</p></div>
                <Link to="/login">Watch Live</Link>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section" id="djs">
          <SectionHeading title="Verified DJs & Club Curators" detail="Stream live DJ sets or fund direct promo spin bounties with escrow protection." action="DJ Bounty Board" />
          <div className="landing-dj-grid">
            {djs.map(([name, location, spins], index) => (
              <article className="landing-dj-card" key={name}>
                <div className="landing-dj-profile"><span className={`landing-dj-avatar landing-dj-avatar-${index + 1}`} aria-hidden="true">{name.slice(3, 4)}</span><div><h3>{name}</h3><span>{location}</span></div></div>
                <div className="landing-dj-spins"><span>Verified Spins</span><strong>{spins}</strong></div>
                <Link to="/login?mode=register">Send Promo</Link>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-join">
          <div><h2>Ready to Join CamerHits?</h2><p>Sign up as a Fan, Artist, DJ, or Event Promoter—instant MTN MoMo wallet included.</p></div>
          <div><Link className="landing-button landing-button-muted" to="/login">Sign In</Link><Link className="landing-button landing-button-primary" to="/login?mode=register">Register Now</Link></div>
        </section>
      </main>

      <footer className="landing-footer">
        <span>CamerHits · Direct Cameroonian Music, Events, TV &amp; DJs</span>
        <nav aria-label="Footer navigation"><a href="#streaming">Streaming</a><a href="#events">Events</a><a href="#tv-channels">TV Channels</a><a href="#djs">DJs</a></nav>
      </footer>
    </div>
  )
}
