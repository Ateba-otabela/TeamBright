import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const DashboardContext = createContext(null)

export const translations = {
  en: {
    role: 'Role', artist: 'Artist', dj: 'DJ', broadcaster: 'Broadcaster', collaborator: 'Collaborator', promoter: 'Promoter', fan: 'Fan', admin: 'Admin',
    language: 'EN / FR', closeNav: 'Close navigation', openNav: 'Open navigation', notifications: 'Notifications', noNotifications: 'No notifications', markRead: 'Mark read', markAllRead: 'Mark all read', notificationOpened: 'Notification opened',
    home: 'Home Overview', catalog: 'Catalog', events: 'Events & Tickets', ai: 'AI Advisor', splits: 'Split Contracts', bounties: 'DJ Bounties', bookings: 'Direct Bookings', transactions: 'Transactions',
    welcome: 'Welcome back', verified: 'Verified Artist', welcomeDetail: 'Direct B2C fan sales and B2B bookings active across Buea, Douala, and Yaoundé.', withdraw: 'Withdraw to MoMo',
    upload: 'Upload Song', uploadDetail: 'Direct B2C & EPK', diagnosis: 'AI Diagnosis', diagnosisDetail: 'Compare Hit Scores', split: 'Split Contract', splitDetail: 'PIN-signed MoMo splits', broadcast: 'Phone Broadcast', broadcastDetail: 'DJ, radio & TV destinations',
    earnings: 'Total Direct Earnings (Mo)', sales: 'Direct B2C Plays & Sales', spins: 'Verified DJ Spins', bountiesMetric: 'B2B Bounties & Bookings',
    revenueTitle: 'Direct Revenue Over Time (XAF)', revenueDetail: 'Comparing B2C fan sales & tickets vs. B2B bounties & direct bookings (Last 30 Days)',
    nextBrief: 'Next Track Brief', inspect: 'Inspect Diagnosis', uploadFlow: 'Upload a track', analysisFlow: 'Track analysis', contractFlow: 'Split contract', broadcastFlow: 'Broadcast request',
  },
  fr: {
    role: 'Rôle', artist: 'Artiste', dj: 'DJ', collaborator: 'Collaborateur', promoter: 'Promoteur', fan: 'Fan', admin: 'Admin',
    language: 'FR / EN', closeNav: 'Fermer la navigation', openNav: 'Ouvrir la navigation', notifications: 'Notifications', noNotifications: 'Aucune notification', markRead: 'Marquer comme lu', markAllRead: 'Tout marquer comme lu', notificationOpened: 'Notification ouverte',
    home: 'Vue d’ensemble', catalog: 'Catalogue', events: 'Événements & Billets', ai: 'Conseiller IA', splits: 'Contrats de partage', bounties: 'Primes DJ', bookings: 'Réservations directes', transactions: 'Transactions',
    welcome: 'Bienvenue', verified: 'Artiste vérifié', welcomeDetail: 'Ventes directes B2C et réservations B2B actives à Buea, Douala et Yaoundé.', withdraw: 'Retirer vers MoMo',
    upload: 'Téléverser un son', uploadDetail: 'B2C direct & EPK', diagnosis: 'Diagnostic IA', diagnosisDetail: 'Comparer les scores', split: 'Contrat de partage', splitDetail: 'Partages MoMo par PIN', broadcast: 'Diffusion téléphonique', broadcastDetail: 'DJ, radio et télévision',
    earnings: 'Revenus directs totaux (mois)', sales: 'Lectures et ventes B2C directes', spins: 'Passages DJ vérifiés', bountiesMetric: 'Primes et réservations B2B',
    revenueTitle: 'Revenus directs dans le temps (XAF)', revenueDetail: 'Comparaison ventes/billets B2C avec primes/réservations B2B (30 derniers jours)',
    nextBrief: 'Prochain plan de titre', inspect: 'Voir le diagnostic', uploadFlow: 'Téléverser un morceau', analysisFlow: 'Analyse du morceau', contractFlow: 'Contrat de partage', broadcastFlow: 'Demande de diffusion',
  },
}

export function DashboardProvider({ children }) {
  const [language, setLanguage] = useState(() => localStorage.getItem('camerhits-language') || 'en')
  const [notifications, setNotifications] = useState(() => {
    const saved = localStorage.getItem('camerhits-notifications')
    return saved ? JSON.parse(saved) : [
      { id: 1, title: 'Midnight Rain score alert', titleFr: 'Alerte score pour Midnight Rain', detail: 'Hit Score dropped to 41.2.', detailFr: 'Le score est passé à 41,2.', read: false },
      { id: 2, title: 'Buea Town Vibe is live', titleFr: 'Buea Town Vibe est en ligne', detail: '218 direct sales recorded.', detailFr: '218 ventes directes enregistrées.', read: false },
      { id: 3, title: 'Douala DJ bounty', titleFr: 'Prime DJ de Douala', detail: '15,000 XAF bounty is open.', detailFr: 'La prime de 15 000 XAF est ouverte.', read: false },
    ]
  })
  const [walletBalance, setWalletBalance] = useState(() => Number(localStorage.getItem('camerhits-wallet') || 284650))
  const [transactions, setTransactions] = useState(() => {
    const saved = localStorage.getItem('camerhits-transactions')
    return saved ? JSON.parse(saved).filter((item) => !/demo|démo/i.test(`${item.status || ''} ${item.statusFr || ''}`)) : []
  })

  useEffect(() => { localStorage.setItem('camerhits-language', language) }, [language])
  useEffect(() => { localStorage.setItem('camerhits-notifications', JSON.stringify(notifications)) }, [notifications])
  useEffect(() => { localStorage.setItem('camerhits-wallet', String(walletBalance)) }, [walletBalance])
  useEffect(() => { localStorage.setItem('camerhits-transactions', JSON.stringify(transactions)) }, [transactions])

  const value = useMemo(() => ({
    language,
    setLanguage,
    t: translations[language],
    notifications,
    unreadCount: notifications.filter((item) => !item.read).length,
    openNotification: (id) => setNotifications((items) => items.map((item) => item.id === id ? { ...item, read: true } : item)),
    markAllRead: () => setNotifications((items) => items.map((item) => ({ ...item, read: true }))),
    walletBalance,
    transactions,
  }), [language, notifications, walletBalance, transactions])

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>
}

export function useDashboard() { return useContext(DashboardContext) }
