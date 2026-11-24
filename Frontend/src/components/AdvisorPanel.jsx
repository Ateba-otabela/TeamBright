import { useState } from 'react'
import { useDashboard } from '../dashboardContext'

export default function AdvisorPanel({ onInspect }) {
  const { t, language } = useDashboard()
  const [briefItems, setBriefItems] = useState([
    { text: 'Hit chorus before 20s (Radio Edit)', done: true },
    { text: 'Lock Producer Njoh 30% MoMo split', done: true },
    { text: 'Test 500 XAF direct fan price', done: false },
    { text: 'Send a track to a Douala radio destination', done: false },
  ])
  const toggleItem = (index) => setBriefItems((items) => items.map((item, i) => i === index ? { ...item, done: !item.done } : item))
  const doneCount = briefItems.filter((item) => item.done).length

  return (
    <div className="advisor-column">
      <article className="advisor-card"><div className="advisor-heading"><span><b>AI ADVISOR</b></span><span className="advisor-badge">-45.2 Hit Score</span></div><h2>{language === 'fr' ? 'Alerte Midnight Rain' : 'Midnight Rain Alert'}</h2><p>{language === 'fr' ? <>Le score est tombé à <strong>41.2</strong> contre <strong>86.4</strong> pour « Buea Town Vibe ». L’introduction de 44 s et le prix de 1 000 XAF freinent les passages DJ à Douala.</> : <>Score dropped to <strong>41.2</strong> vs. <strong>86.4</strong> on “Buea Town Vibe”. 44s intro delay and 1,000 XAF pricing are slowing Douala DJ spins.</>}</p><div className="tags"><span>SLOW_HOOK</span><span>DJ_FRICTION</span><span>PRICE_RESISTANCE</span></div><button className="primary-button full" type="button" onClick={onInspect}>{t.inspect} <span className="material-icon">arrow_forward</span></button></article>
      <article className="brief-card"><div className="brief-heading"><h2>{t.nextBrief}</h2><span>{doneCount}/4 {language === 'fr' ? 'fait' : 'Done'}</span></div><ul>{briefItems.map((item, index) => <li key={item.text}><button type="button" className={item.done ? 'done' : ''} onClick={() => toggleItem(index)}><span className="material-icon">{item.done ? 'check_circle' : 'radio_button_unchecked'}</span><span>{item.text}</span></button></li>)}</ul></article>
    </div>
  )
}
