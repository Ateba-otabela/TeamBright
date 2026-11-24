export default function StatCard({ label, value, detail, badge }) {
  return <article className="stat-card"><small>{label}</small>{badge && <span className="stat-badge">{badge}</span>}<strong>{value}</strong><span>{detail}</span></article>
}
