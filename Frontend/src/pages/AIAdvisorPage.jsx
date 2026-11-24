import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../authContext'
import { apiClient, getApiErrorMessage } from '../services/api/client'

function formatFixes(fixes) {
  if (Array.isArray(fixes)) return fixes.join(' ')
  if (typeof fixes === 'string') return fixes
  return 'No recommended fixes were returned.'
}

export default function AIAdvisorPage() {
  const { user } = useAuth()
  const [studio, setStudio] = useState({ benchmarks: [], demos: [] })
  const [advisor, setAdvisor] = useState(null)
  const [benchmarkTitle, setBenchmarkTitle] = useState('')
  const [benchmarkGenre, setBenchmarkGenre] = useState('')
  const [benchmarkFile, setBenchmarkFile] = useState(null)
  const [demoTitle, setDemoTitle] = useState('')
  const [benchmarkId, setBenchmarkId] = useState('')
  const [demoFile, setDemoFile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [studioResponse, advisorResponse] = await Promise.all([
        apiClient.get('/analyzer/my-studio'),
        apiClient.get('/advisor/dashboard'),
      ])
      setStudio(studioResponse.data)
      setAdvisor(advisorResponse.data)
      setBenchmarkId((current) => current || String(studioResponse.data.benchmarks[0]?.id || ''))
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Could not load advisor data.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const createBenchmark = async (event) => {
    event.preventDefault()
    if (!benchmarkFile) {
      setError('Choose an audio file for the benchmark.')
      return
    }
    setSubmitting(true)
    setError('')
    setNotice('')
    try {
      const formData = new FormData()
      formData.append('title', benchmarkTitle.trim())
      formData.append('genre', benchmarkGenre.trim())
      formData.append('audio_file', benchmarkFile)
      await apiClient.post('/analyzer/viral-benchmarks', formData, { timeout: 120_000 })
      setBenchmarkTitle('')
      setBenchmarkGenre('')
      setBenchmarkFile(null)
      setNotice('Benchmark analyzed and saved.')
      await loadData()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Could not analyze this benchmark.'))
    } finally {
      setSubmitting(false)
    }
  }

  const compareDemo = async (event) => {
    event.preventDefault()
    if (!demoFile || !benchmarkId) {
      setError('Choose a benchmark and an audio file to compare.')
      return
    }
    setSubmitting(true)
    setError('')
    setNotice('')
    try {
      const formData = new FormData()
      formData.append('benchmark_id', benchmarkId)
      formData.append('demo_title', demoTitle.trim())
      formData.append('audio_file', demoFile)
      await apiClient.post('/analyzer/compare', formData, { timeout: 120_000 })
      setDemoTitle('')
      setDemoFile(null)
      setNotice('Studio comparison completed and saved.')
      await loadData()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Could not compare this demo.'))
    } finally {
      setSubmitting(false)
    }
  }

  const acknowledgeInsight = async (insightId) => {
    setError('')
    try {
      await apiClient.post(`/advisor/insights/${insightId}/acknowledge`)
      await loadData()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Could not acknowledge this insight.'))
    }
  }

  return (
    <main className="ai-advisor-page">
      <section className="advisor-comparison-header">
        <div><span className="broadcast-eyebrow">CamerHits · Live API</span><h1>AI Advisor &amp; SoundDNA Studio</h1><p>Upload an audio benchmark, compare studio demos, and review release insights from the backend.</p></div>
        <div className="advisor-flags"><b>{advisor?.weekly_momentum_status?.replaceAll('_', ' ') || 'No release data'}</b><span>{advisor?.unread_alerts_count || 0} unread insights</span></div>
      </section>

      {error && <p className="form-error" role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      {loading && <p role="status">Loading analyzer and advisor data…</p>}

      {user?.role === 'artist' && <section className="advisor-visual-grid">
        <form className="waveform-card dashboard-form" onSubmit={createBenchmark}>
          <div className="advisor-panel-heading"><h2>Create a viral benchmark</h2><span>SoundDNA</span></div>
          <label><span>Benchmark title *</span><input value={benchmarkTitle} onChange={(event) => setBenchmarkTitle(event.target.value)} maxLength={200} required /></label>
          <label><span>Genre *</span><input value={benchmarkGenre} onChange={(event) => setBenchmarkGenre(event.target.value)} maxLength={100} required /></label>
          <label><span>Audio file *</span><input type="file" accept="audio/*,.wav,.mp3,.flac" onChange={(event) => setBenchmarkFile(event.target.files?.[0] || null)} required /></label>
          <button className="primary-button" type="submit" disabled={submitting}>{submitting ? 'Analyzing…' : 'Analyze benchmark'}</button>
        </form>

        <form className="waveform-card dashboard-form" onSubmit={compareDemo}>
          <div className="advisor-panel-heading"><h2>Compare a studio demo</h2><span>Versioned analysis</span></div>
          <label><span>Benchmark *</span><select value={benchmarkId} onChange={(event) => setBenchmarkId(event.target.value)} required><option value="">Select benchmark</option>{studio.benchmarks.map((item) => <option key={item.id} value={item.id}>{item.title} · {item.genre}</option>)}</select></label>
          <label><span>Demo title *</span><input value={demoTitle} onChange={(event) => setDemoTitle(event.target.value)} maxLength={200} required /></label>
          <label><span>Audio file *</span><input type="file" accept="audio/*,.wav,.mp3,.flac" onChange={(event) => setDemoFile(event.target.files?.[0] || null)} required /></label>
          <button className="primary-button" type="submit" disabled={submitting || !studio.benchmarks.length}>{submitting ? 'Comparing…' : 'Compare demo'}</button>
        </form>
      </section>}

      <section className="diagnostic-table-card">
        <div className="diagnostic-table-heading"><h2>Saved Studio Analyses</h2><span>{studio.demos.length} comparison{studio.demos.length === 1 ? '' : 's'}</span></div>
        {studio.demos.length === 0 ? <p className="advisor-empty">No analyses yet. Artists can create a benchmark and compare a demo above.</p> : <div className="diagnostic-table-wrap"><table><thead><tr><th>Demo</th><th>Benchmark</th><th>Version</th><th>Hit readiness</th><th>Verdict</th><th>Studio fixes</th></tr></thead><tbody>{studio.demos.map((demo) => <tr key={demo.id}><td>{demo.demo_title}</td><td>{studio.benchmarks.find((item) => item.id === demo.benchmark_id)?.title || `#${demo.benchmark_id}`}</td><td>{demo.version}</td><td>{demo.scores.hit_readiness_score}</td><td>{demo.verdict}</td><td>{formatFixes(demo.studio_fixes)}</td></tr>)}</tbody></table></div>}
      </section>

      <section className="diagnostic-table-card">
        <div className="diagnostic-table-heading"><h2>Release Insights</h2><span>{advisor?.trajectory?.length || 0} signal snapshots</span></div>
        {!advisor?.insights?.length ? <p className="advisor-empty">No release insights are available yet. Publish a release and submit a weekly signal snapshot to start the advisor.</p> : <div className="advisor-insights">{advisor.insights.map((insight) => <article className="advisor-insight" key={insight.id}><div><strong>{insight.title}</strong><p>{insight.recommendation}</p><small>{insight.category} · {insight.priority}</small></div>{!insight.acknowledged && <button className="event-outline-button" type="button" onClick={() => acknowledgeInsight(insight.id)}>Acknowledge</button>}</article>)}</div>}
      </section>
    </main>
  )
}
