const kpis = [
  { label: 'Total lignes', value: '128' },
  { label: 'Matricules uniques', value: '97' },
  { label: 'PC inventoriés', value: '112' }
]

export function Dashboard() {
  return (
    <section>
      <h2>Tableau de bord</h2>
      <div className="kpi-grid">
        {kpis.map((kpi) => (
          <article className="kpi-card" key={kpi.label}>
            <span>{kpi.label}</span>
            <strong>{kpi.value}</strong>
          </article>
        ))}
      </div>
      <div className="panel">
        <p>
          Cette base Vite/TypeScript est prête pour connecter vos APIs backend
          (Streamlit, FastAPI ou n8n webhook).
        </p>
      </div>
    </section>
  )
}
