import { useState } from 'react'
import { Link } from 'react-router-dom'

function Waveform({ variant = 'benchmark' }) {
  const benchmark = [12,20,16,24,28,32,44,48,40,48,36,44,48,36,44,40,48,32,44,40,48,36,40,32]
  const rain = [8,12,8,16,12,16,12,16,20,16,12,20,16,24,20,28]
  const bars = variant === 'benchmark' ? benchmark : rain

  return (
    <svg viewBox="0 0 600 56" className="advisor-waveform" role="img" aria-label={variant === 'benchmark' ? 'Buea Town Vibe waveform' : 'Midnight Rain waveform'}>
      <g className={variant === 'benchmark' ? 'waveform-benchmark' : 'waveform-rain'}>
        {bars.map((height, index) => {
          const x = variant === 'benchmark' ? 8 + index * 10 : 8 + index * 10
          const y = (56 - height) / 2
          return <rect key={index} x={x} y={y} width="4" height={height} rx="2" />
        })}
      </g>
      {variant === 'benchmark' ? <><line x1="74" y1="0" x2="74" y2="56" className="chorus-line"/><text x="78" y="12" className="chorus-text benchmark">18s CHORUS</text></> : <><line x1="174" y1="0" x2="174" y2="56" className="chorus-line rain"/><text x="178" y="12" className="chorus-text rain">44s CHORUS</text></>}
    </svg>
  )
}

function SonicRadar() {
  return (
    <article className="sonic-radar-card">
      <div className="advisor-panel-heading"><h2>Sonic Benchmark</h2><span>6-Axis Radar</span></div>
      <svg viewBox="0 0 280 220" className="sonic-radar" role="img" aria-label="Sonic benchmark radar chart">
        <g className="radar-rings"><polygon points="140,24 218,69 218,159 140,204 62,159 62,69"/><polygon points="140,54 192,84 192,144 140,174 88,144 88,84"/><polygon points="140,84 166,99 166,129 140,144 114,129 114,99"/></g>
        <polygon className="radar-benchmark" points="140,34 206,75 210,154 140,190 74,150 78,76"/>
        <polygon className="radar-rain" points="140,68 178,94 168,136 140,162 96,138 102,92"/>
        <g className="radar-labels"><text x="122" y="16">Tempo</text><text x="224" y="72">Energy</text><text x="224" y="164">Hook Speed</text><text x="104" y="216">Vocal Presence</text><text x="4" y="164">Repetition</text><text x="8" y="72">Loudness</text></g>
      </svg>
      <div className="radar-legend"><span><i className="solid"/>Buea Town Vibe</span><span><i className="dashed"/>Midnight Rain</span></div>
    </article>
  )
}

const metricRows = [
  ['Time to chorus', '18s', '44s', '+26s intro delay'],
  ['DJ downloads', '500', '500', 'Equal top-of-funnel reach'],
  ['DJ spins', '450 (90.0%)', '171 (34.2%)', '-55.8pt drop in Douala'],
  ['Avg listen completion', '82%', '48%', '-34% drop-off before chorus'],
  ['Preview plays', '4,000', '3,000', '-1,000 organic previews'],
  ['Sales & conversion', '218 (5.45%)', '122 (4.07%)', '-1.38% conversion drag'],
  ['Direct B2C Price', '500 XAF', '1,000 XAF', '2x price friction'],
]

export default function AIAdvisorPage() {
  const [benchmark, setBenchmark] = useState('Buea Town Vibe (Hit Score 86.4)')
  const [diagnosed, setDiagnosed] = useState('Midnight Rain (Hit Score 41.2)')
  const [chatText, setChatText] = useState('')
  const [saved, setSaved] = useState(false)
  const [priceConfirm, setPriceConfirm] = useState(false)

  const saveBrief = () => {
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1800)
  }

  return (
    <main className="ai-advisor-page">
      <section className="advisor-comparison-header">
        <div className="track-selectors">
          <label><span>Benchmark Track (A)</span><select value={benchmark} onChange={(event) => setBenchmark(event.target.value)} aria-label="Benchmark track"><option>Buea Town Vibe (Hit Score 86.4)</option><option>Bamenda Sunrise (Draft)</option></select></label>
          <b>VS</b>
          <label><span>Diagnosed Track (B)</span><select value={diagnosed} onChange={(event) => setDiagnosed(event.target.value)} aria-label="Diagnosed track"><option>Midnight Rain (Hit Score 41.2)</option><option>Douala Dusk (Archive)</option></select></label>
        </div>
        <div className="advisor-flags"><b><span className="material-icon">arrow_downward</span>-45.2 Score Delta</b><span>[SLOW_HOOK]</span><span>[DJ_FRICTION]</span><span>[PRICE_RESISTANCE]</span></div>
      </section>

      <section className="advisor-visual-grid">
        <article className="waveform-card">
          <div className="advisor-panel-heading"><h2>Chorus Entry &amp; Waveform Alignment</h2><b>+26s Hook Delay</b></div>
          <div className="waveform-row"><div><strong className="benchmark-name">Buea Town Vibe (86.4)</strong><span>Chorus at 18s</span></div><div className="waveform-frame benchmark"><Waveform /></div></div>
          <div className="waveform-row"><div><strong>Midnight Rain (41.2)</strong><span>Chorus at 44s (+26s delay)</span></div><div className="waveform-frame rain"><Waveform variant="rain" /></div></div>
        </article>
        <SonicRadar />
      </section>

      <section className="diagnostic-table-card">
        <div className="diagnostic-table-heading"><h2>Diagnostic Metric Breakdown &amp; Conversion Funnel</h2><span>Weights: Hook 25% • DJ Traction 30% • Retention 25% • Monetization 20%</span></div>
        <div className="diagnostic-table-wrap"><table><thead><tr><th>Metric</th><th className="benchmark-column">{benchmark.includes('Buea') ? 'Buea Town Vibe (86.4)' : 'Bamenda Sunrise (Draft)'}</th><th>{diagnosed.includes('Midnight') ? 'Midnight Rain (41.2)' : 'Douala Dusk (Archive)'}</th><th>Diagnostic Impact</th></tr></thead><tbody>{metricRows.map((row) => <tr key={row[0]}>{row.map((cell, index) => <td key={index} className={index === 1 ? 'benchmark-column' : index === 3 ? 'impact-column' : ''}>{cell}</td>)}</tr>)}</tbody></table></div>
      </section>

      <section className="advisor-action-grid">
        <article className="root-cause-card">
          <div><div className="advisor-panel-heading"><b><span className="material-icon">auto_awesome</span>AI ADVISOR • ROOT CAUSE PRESCRIPTION</b></div><p className="root-cause">&quot;Midnight Rain&quot; loses 55.8% of Douala DJs because the 44s intro stalls club energy, while the 1,000 XAF price slows fan impulse buys.</p><p className="pattern-note">Pattern match based on Cameroonian hit benchmarks — likely drivers, not guarantees.</p></div>
          <div className="advisor-tools">
            <button type="button"><b>[RADIO_EDIT]</b><span>Trim 20s intro to hit chorus by 24s</span></button>
            <Link to="/phone-broadcast"><b>[PHONE_BROADCAST]</b><span>Send a track to a Douala radio destination</span></Link>
            <button type="button" className="outlined" onClick={() => setPriceConfirm((value) => !value)}><b>[PRICE_DROP]</b><span>{priceConfirm ? '500 XAF test confirmed' : 'Test 500 XAF direct fan price (Confirm)'}</span></button>
            <button type="button" className="outlined"><b>[CITY_TARGETING]</b><span>Open Buea / Douala listener heatmap</span></button>
          </div>
        </article>

        <aside className="advisor-followup-card">
          <div className="split-check"><div><strong>Smart-Contract Check</strong><span>Confirm Producer Njoh 30% split before boosting</span></div><Link to="/split-contracts">Verify Split</Link></div>
          <div className="advisor-chat"><div className="advisor-chat-message"><strong>AI Advisor:</strong><p>Ready to trim 0:00–0:20 on &quot;Midnight Rain&quot; and re-export the &lt;500 KB preview?</p></div><div className="chat-controls"><input value={chatText} onChange={(event) => setChatText(event.target.value)} placeholder="Ask AI Advisor about Douala DJs..."/><button type="button" onClick={saveBrief}>{saved ? 'Saved to Brief' : 'Save to Next Track Brief'}</button></div></div>
        </aside>
      </section>
    </main>
  )
}
