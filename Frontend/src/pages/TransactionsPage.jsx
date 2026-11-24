import { useMemo, useState } from 'react'
import { useDashboard } from '../dashboardContext'

const paymentMethods = ['MTN MoMo •• 650', 'Orange Money •• 690', 'Saved payout •• 237']
const services = ['DJ Nzo', 'Hit FM Cameroon', 'CRTV Channel 1', 'Buea Sound Radio', 'Producer Njoh']

export default function TransactionsPage() {
  const { language, walletBalance, transactions, submitDemoTransaction } = useDashboard()
  const fr = language === 'fr'
  const [action, setAction] = useState('add')
  const [amount, setAmount] = useState('')
  const [destination, setDestination] = useState(paymentMethods[0])
  const [number, setNumber] = useState('+237 ')
  const [note, setNote] = useState('')
  const [step, setStep] = useState('form')
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const fee = useMemo(() => {
    const value = Number(amount)
    if (!Number.isFinite(value) || value <= 0) return 0
    return action === 'fund' ? Math.round(value * 0.02) : action === 'withdraw' ? 500 : 0
  }, [action, amount])

  const resetAction = (nextAction) => {
    setAction(nextAction)
    setAmount('')
    setDestination(nextAction === 'fund' ? services[0] : nextAction === 'withdraw' ? '+237 ' : paymentMethods[0])
    setNumber('+237 ')
    setNote('')
    setStep('form')
    setError('')
    setSubmitted(false)
  }

  const review = (event) => {
    event.preventDefault()
    setError('')
    const value = Number(amount)
    if (!amount || !Number.isFinite(value) || value <= 0) return setError(fr ? 'Saisissez un montant supérieur à zéro.' : 'Enter an amount greater than zero.')
    if (action === 'add' && !destination.trim()) return setError(fr ? 'Choisissez ou saisissez une méthode de paiement.' : 'Choose or enter a payment method.')
    if (action === 'withdraw' && number.replace(/\D/g, '').length < 9) return setError(fr ? 'Saisissez un numéro MoMo valide.' : 'Enter a valid MoMo number.')
    if (action === 'fund' && !destination.trim()) return setError(fr ? 'Choisissez un DJ ou un service.' : 'Choose a DJ or service.')
    setStep('review')
  }

  const submit = () => {
    submitDemoTransaction({ type: action, amount: Number(amount), destination: action === 'withdraw' ? number.trim() : destination, fee, note })
    setSubmitted(true)
  }

  const labels = {
    add: fr ? 'Ajouter de l’argent' : 'Add money',
    withdraw: fr ? 'Retirer' : 'Withdraw',
    fund: fr ? 'Financer un DJ ou service' : 'Fund a DJ or service',
  }

  return (
    <main className="transactions-page">
      <section className="transactions-heading"><div><span className="transactions-eyebrow">CamerHits • {fr ? 'Transactions démo' : 'Demo transactions'}</span><h1>{fr ? 'Transactions' : 'Transactions'}</h1><p>{fr ? 'Gérez votre solde avec un parcours de démonstration clairement identifié.' : 'Manage your wallet with a clearly labeled demo flow.'}</p></div><div className="wallet-balance"><small>{fr ? 'Solde du portefeuille' : 'Wallet balance'}</small><strong>{walletBalance.toLocaleString()} XAF</strong></div></section>

      <section className="transaction-layout">
        <aside className="transaction-actions" aria-label={fr ? 'Actions de transaction' : 'Transaction actions'}>
          {[['add', 'add'], ['withdraw', 'payments'], ['fund', 'campaign']].map(([value, icon]) => <button type="button" key={value} className={action === value ? 'active' : ''} onClick={() => resetAction(value)}><span className="material-icon">{icon}</span><span>{labels[value]}</span></button>)}
        </aside>

        <div className="transaction-workspace">
          {submitted ? <div className="success-panel transaction-success" role="status"><span className="material-icon">check_circle</span><div><strong>{fr ? 'Transaction démo confirmée' : 'Demo transaction confirmed'}</strong><p>{fr ? 'Aucun argent réel n’a été ajouté, retiré ou transféré. La transaction a été ajoutée à l’historique.' : 'No real money was added, withdrawn, or transferred. The transaction was added to history.'}</p></div></div> : step === 'form' ? <form className="dashboard-form transaction-form" onSubmit={review}>
            <h2>{labels[action]}</h2>
            {action === 'add' && <><label><span>{fr ? 'Méthode MoMo' : 'MoMo payment method'} *</span><select value={destination} onChange={(event) => setDestination(event.target.value)}>{paymentMethods.map((item) => <option key={item}>{item}</option>)}</select></label><label><span>{fr ? 'Ou saisir une méthode' : 'Or enter a method'}</span><input value={destination} onChange={(event) => setDestination(event.target.value)} placeholder="MTN MoMo / Orange Money" /></label></>}
            {action === 'withdraw' && <><label><span>{fr ? 'Numéro MoMo ou compte enregistré' : 'MoMo number or saved payout account'} *</span><input value={number} onChange={(event) => setNumber(event.target.value)} placeholder="+237 6XX XXX XXX" /></label></>}
            {action === 'fund' && <><label><span>{fr ? 'DJ ou service' : 'DJ or service'} *</span><select value={destination} onChange={(event) => setDestination(event.target.value)}>{services.map((item) => <option key={item}>{item}</option>)}</select></label><label><span>{fr ? 'Note facultative' : 'Optional note'}</span><textarea rows="3" value={note} onChange={(event) => setNote(event.target.value)} placeholder={fr ? 'Objectif ou détails du financement' : 'Funding purpose or details'} /></label></>}
            <label><span>{fr ? 'Montant (XAF)' : 'Amount (XAF)'} *</span><input type="number" min="1" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
            {error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button full" type="submit">{fr ? 'Passer en revue' : 'Review Transaction'}</button>
          </form> : <div className="review-panel"><span className="demo-banner">{fr ? 'Vérifiez les détails — soumission démo uniquement' : 'Review details — demo submission only'}</span><h2>{labels[action]}</h2><dl><div><dt>{fr ? 'Montant' : 'Amount'}</dt><dd>{Number(amount).toLocaleString()} XAF</dd></div><div><dt>{fr ? 'Destination' : 'Destination'}</dt><dd>{action === 'withdraw' ? number : destination}</dd></div><div><dt>{fr ? 'Frais applicables' : 'Applicable fees'}</dt><dd>{fee.toLocaleString()} XAF</dd></div>{note && <div><dt>{fr ? 'Note' : 'Note'}</dt><dd>{note}</dd></div>}</dl><p>{fr ? 'Aucun paiement réel ne sera initié.' : 'No real payment will be initiated.'}</p><div className="form-actions"><button className="secondary-button" type="button" onClick={() => setStep('form')}>{fr ? 'Modifier' : 'Edit'}</button><button className="primary-button" type="button" onClick={submit}>{fr ? 'Confirmer la transaction démo' : 'Confirm Demo Transaction'}</button></div></div>}
        </div>
      </section>

      <section className="transaction-history"><div className="history-heading"><h2>{fr ? 'Historique des transactions' : 'Transaction history'}</h2><span>{transactions.length} {fr ? 'transactions' : 'transactions'}</span></div><div className="history-table-wrap"><table><thead><tr><th>{fr ? 'Date' : 'Date'}</th><th>{fr ? 'Type' : 'Type'}</th><th>{fr ? 'Destination' : 'Destination'}</th><th>{fr ? 'Montant' : 'Amount'}</th><th>{fr ? 'Statut' : 'Status'}</th></tr></thead><tbody>{transactions.map((item) => <tr key={item.id}><td>{item.date}</td><td>{fr ? item.typeFr : item.type}</td><td>{item.destination}</td><td className={item.type === 'Withdrawal' ? 'outflow' : 'inflow'}>{item.type === 'Withdrawal' || item.type === 'DJ / service funding' ? '−' : '+'}{item.amount.toLocaleString()} XAF</td><td><span className="transaction-status">{fr ? item.statusFr : item.status}</span></td></tr>)}</tbody></table></div></section>
    </main>
  )
}
