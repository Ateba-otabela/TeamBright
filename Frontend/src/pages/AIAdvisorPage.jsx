import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useDashboard } from '../dashboardContext'

function SonicRadar({ metrics, playing }) {
  const livePoints = metrics.map((value, index) => {
    const angle = (-90 + index * 60) * Math.PI / 180
    const radius = 12 + value * 82
    return `${140 + Math.cos(angle) * radius},${112 + Math.sin(angle) * radius}`
  }).join(' ')
  return (
    <article className="sonic-radar-card">
      <div className="advisor-panel-heading"><h2>Go Na GO Sonic Analysis</h2><span>{playing ? 'LIVE' : 'LIVE WHEN PLAYING'}</span></div>
      <svg viewBox="0 0 280 220" className="sonic-radar" role="img" aria-label="Live Go Na GO frequency band analysis">
        <g className="radar-rings"><polygon points="140,24 216,68 216,156 140,200 64,156 64,68"/><polygon points="140,52 192,82 192,142 140,172 88,142 88,82"/><polygon points="140,80 168,96 168,128 140,144 112,128 112,96"/></g>
        <polygon className="radar-live-spectrum" points={livePoints}/>
        <g className="radar-labels"><text x="112" y="16">Sub bass</text><text x="220" y="70">Bass</text><text x="214" y="164">Low-mid</text><text x="118" y="216">Mid</text><text x="10" y="164">High-mid</text><text x="16" y="70">Treble</text></g>
      </svg>
      <div className="radar-legend"><span><i className="solid"/>Go Na GO — KOCEE</span><span>{playing ? 'Spectrum updates during playback' : 'Press Play to analyze the audio'}</span></div>
    </article>
  )
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return '0:00'
  const minutes = Math.floor(seconds / 60)
  const remainder = Math.floor(seconds % 60).toString().padStart(2, '0')
  return `${minutes}:${remainder}`
}

function GoNaGoPlayer({ fr, onSpectrum, onPlayback }) {
  const audioRef = useRef(null)
  const canvasRef = useRef(null)
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const sourceRef = useRef(null)
  const objectUrlRef = useRef('')
  const animationRef = useRef(0)
  const lastRadarUpdateRef = useRef(0)
  const [audioUrl, setAudioUrl] = useState('/audio/go-na-go.m4a')
  const [fileName, setFileName] = useState('Go Na GO — KOCEE')
  const [playing, setPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [audioError, setAudioError] = useState('')

  useEffect(() => () => {
    window.cancelAnimationFrame(animationRef.current)
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    audioContextRef.current?.close().catch(() => {})
  }, [])

  const loadAudio = (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (!file.type.startsWith('audio/') && !/\.(mp3|wav|m4a|aac|flac|ogg)$/i.test(file.name)) {
      setAudioError(fr ? 'Choisissez un fichier audio valide.' : 'Choose a valid audio file.')
      return
    }
    audioRef.current?.pause()
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    const url = URL.createObjectURL(file)
    objectUrlRef.current = url
    setAudioUrl(url)
    setFileName(file.name)
    setCurrentTime(0)
    setDuration(0)
    setPlaying(false)
    setAudioError('')
    window.cancelAnimationFrame(animationRef.current)
  }

  const drawFrequencyBars = () => {
    const analyser = analyserRef.current
    const canvas = canvasRef.current
    if (!analyser || !canvas) return
    const bounds = canvas.getBoundingClientRect()
    const pixelRatio = window.devicePixelRatio || 1
    const width = Math.max(1, Math.floor(bounds.width * pixelRatio))
    const height = Math.max(1, Math.floor(bounds.height * pixelRatio))
    if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height }
    const context = canvas.getContext('2d')
    if (!context) return
    context.clearRect(0, 0, width, height)
    const values = new Uint8Array(analyser.frequencyBinCount)
    analyser.getByteFrequencyData(values)
    const bars = 48
    const gap = 2 * pixelRatio
    const barWidth = Math.max(1, width / bars - gap)
    context.fillStyle = '#ffc629'
    for (let index = 0; index < bars; index += 1) {
      const bin = Math.min(values.length - 1, Math.floor(index * values.length / bars))
      const magnitude = Math.sqrt(values[bin] / 255)
      const barHeight = Math.max(3 * pixelRatio, magnitude * height)
      const x = index * width / bars
      context.fillRect(x, (height - barHeight) / 2, barWidth, barHeight)
    }
    if (Date.now() - lastRadarUpdateRef.current > 120) {
      const ranges = [[0, 3], [3, 8], [8, 16], [16, 32], [32, 64], [64, 128]]
      const metrics = ranges.map(([start, end]) => {
        const segment = values.slice(start, Math.min(end, values.length))
        const average = segment.length ? segment.reduce((sum, value) => sum + value, 0) / segment.length : 0
        return Math.min(1, Math.sqrt(average / 180))
      })
      onSpectrum(metrics)
      lastRadarUpdateRef.current = Date.now()
    }
    animationRef.current = window.requestAnimationFrame(drawFrequencyBars)
  }

  const togglePlayback = async () => {
    const audio = audioRef.current
    if (!audio || !audioUrl) return
    if (!audioContextRef.current) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext
      if (!AudioContextClass) {
        setAudioError(fr ? 'La visualisation des fréquences n’est pas prise en charge par ce navigateur.' : 'Frequency visualization is not supported by this browser.')
        return
      }
      const audioContext = new AudioContextClass()
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.78
      const source = audioContext.createMediaElementSource(audio)
      source.connect(analyser)
      analyser.connect(audioContext.destination)
      audioContextRef.current = audioContext
      analyserRef.current = analyser
      sourceRef.current = source
    }
    try {
      if (audio.paused) {
        await audioContextRef.current.resume()
        await audio.play()
        setPlaying(true)
        onPlayback(true)
        setAudioError('')
        drawFrequencyBars()
      } else {
        audio.pause()
        setPlaying(false)
        onPlayback(false)
        window.cancelAnimationFrame(animationRef.current)
      }
    } catch {
      setAudioError(fr ? 'Ce fichier ne peut pas être lu dans votre navigateur.' : 'Your browser could not play this audio file.')
    }
  }

  const seekTo = (event) => {
    const value = Number(event.target.value)
    if (audioRef.current) audioRef.current.currentTime = value
    setCurrentTime(value)
  }

  const clearVisualizer = () => {
    window.cancelAnimationFrame(animationRef.current)
    const canvas = canvasRef.current
    const context = canvas?.getContext('2d')
    if (canvas && context) context.clearRect(0, 0, canvas.width, canvas.height)
    onSpectrum([0, 0, 0, 0, 0, 0])
  }

  return (
    <div className="go-na-go-player">
      <audio ref={audioRef} src={audioUrl || undefined} preload="metadata" onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)} onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)} onEnded={() => { setPlaying(false); onPlayback(false); clearVisualizer() }} onPause={() => { setPlaying(false); onPlayback(false); clearVisualizer() }} />
      <div className="go-na-go-player-heading"><strong className="benchmark-name">Go Na GO — KOCEE</strong><span>{fr ? 'Refrain à 16 s' : 'Chorus at 16s'}</span></div>
      <div className="waveform-frame benchmark go-na-go-waveform" role="img" aria-label={fr ? 'Visualisation continue des fréquences audio' : 'Live audio frequency visualization'}>
        <canvas ref={canvasRef} aria-hidden="true" />
        {!playing && <span className="frequency-idle-hint">{fr ? 'Appuyez sur Lire pour voir les fréquences en direct' : 'Press Play to see the live frequencies'}</span>}
      </div>
      <div className="go-na-go-controls">
        <button type="button" className="play-audio-button" onClick={togglePlayback} disabled={!audioUrl} aria-label={playing ? (fr ? 'Mettre en pause' : 'Pause') : (fr ? 'Lire' : 'Play')}>
          <span className="material-icon">{playing ? 'pause' : 'play_arrow'}</span>{playing ? (fr ? 'Pause' : 'Pause') : (fr ? 'Lire' : 'Play')}
        </button>
        <span className="audio-time">{formatTime(currentTime)}</span>
        <input aria-label={fr ? 'Position audio' : 'Audio position'} type="range" min="0" max={duration || 0} step="0.1" value={Math.min(currentTime, duration || 0)} onChange={seekTo} disabled={!duration} />
        <span className="audio-time">{formatTime(duration)}</span>
        <label className="audio-file-button"><span className="material-icon">audio_file</span>{fileName ? (fr ? 'Changer l’audio' : 'Change audio') : (fr ? 'Choisir Go Na GO' : 'Choose Go Na GO audio')}<input type="file" accept="audio/*,.mp3,.wav,.m4a,.aac,.flac,.ogg" onChange={loadAudio} /></label>
      </div>
      <p className="audio-file-note">{fileName || (fr ? 'Sélectionnez le fichier audio Go Na GO enregistré sur votre appareil.' : 'Select the Go Na GO audio file saved on your device.')}</p>
      {audioError && <p className="audio-error" role="status">{audioError}</p>}
    </div>
  )
}

const spectrumBands = ['Sub bass', 'Bass', 'Low-mid', 'Mid', 'High-mid', 'Treble']

export default function AIAdvisorPage() {
  const { language } = useDashboard()
  const fr = language === 'fr'
  const [chatText, setChatText] = useState('')
  const [saved, setSaved] = useState(false)
  const [sonicMetrics, setSonicMetrics] = useState([0, 0, 0, 0, 0, 0])
  const [audioPlaying, setAudioPlaying] = useState(false)

  const saveBrief = () => {
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1800)
  }

  return (
    <main className="ai-advisor-page">
      <section className="advisor-comparison-header">
        <div className="track-selectors"><div><span>TRACK IN ANALYSIS</span><strong>Go Na GO — KOCEE</strong></div></div>
        <div className="advisor-flags"><b><span className="material-icon">graphic_eq</span>{audioPlaying ? 'AUDIO PLAYING' : 'AUDIO READY'}</b><span>LIVE SPECTRUM</span></div>
      </section>

      <section className="advisor-visual-grid">
        <article className="waveform-card">
          <div className="advisor-panel-heading"><h2>Chorus Entry &amp; Waveform Alignment</h2></div>
          <GoNaGoPlayer fr={fr} onSpectrum={setSonicMetrics} onPlayback={setAudioPlaying} />
        </article>
        <SonicRadar metrics={sonicMetrics} playing={audioPlaying} />
      </section>

      <section className="diagnostic-table-card">
        <div className="diagnostic-table-heading"><h2>Go Na GO Live Frequency Profile</h2><span>{audioPlaying ? 'Values update during playback' : 'Press Play to analyze the recording'}</span></div>
        <div className="diagnostic-table-wrap"><table><thead><tr><th>Frequency band</th><th>Live intensity</th><th>What it represents</th></tr></thead><tbody>{spectrumBands.map((band, index) => <tr key={band}><td>{band}</td><td>{audioPlaying ? `${Math.round(sonicMetrics[index] * 100)}%` : '—'}</td><td>{['Deep low frequencies', 'Low-end punch', 'Warmth and body', 'Main musical range', 'Presence and detail', 'High-frequency brightness'][index]}</td></tr>)}</tbody></table></div>
      </section>

      <section className="advisor-action-grid">
        <article className="root-cause-card">
          <div><div className="advisor-panel-heading"><b><span className="material-icon">auto_awesome</span>GO NA GO • AUDIO REVIEW</b></div><p className="root-cause">Play Go Na GO to inspect how its low, mid, and high frequency energy changes across the recording.</p><p className="pattern-note">This live spectrum describes the audio signal; audience engagement and virality require listener and DJ performance data.</p></div>
          <div className="advisor-tools">
            <button type="button"><b>[AUDIO_REVIEW]</b><span>Listen for changes in the live frequency profile</span></button>
            <Link to="/phone-broadcast"><b>[PHONE_BROADCAST]</b><span>Send Go Na GO to a radio destination</span></Link>
            <Link to="/catalog" className="outlined"><b>[TRACK_CATALOG]</b><span>Open Go Na GO in the catalog</span></Link>
          </div>
        </article>

        <aside className="advisor-followup-card">
          <div className="split-check"><div><strong>Go Na GO release setup</strong><span>Review its collaborator split before promotion</span></div><Link to="/split-contracts">Review Split</Link></div>
          <div className="advisor-chat"><div className="advisor-chat-message"><strong>AI Advisor:</strong><p>Use the live spectrum and your performance data to build a Go Na GO promotion brief.</p></div><div className="chat-controls"><input value={chatText} onChange={(event) => setChatText(event.target.value)} placeholder="Add a note for the Go Na GO brief..."/><button type="button" onClick={saveBrief}>{saved ? 'Saved to Brief' : 'Save to Next Track Brief'}</button></div></div>
        </aside>
      </section>
    </main>
  )
}
