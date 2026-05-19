import { Sidebar } from './components/Sidebar'
import { Dashboard } from './components/Dashboard'

export default function App() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="content">
        <header className="page-header">
          <h1>Suivi & Affectation PC</h1>
          <p>Frontend Vite + TypeScript (Full Dark)</p>
        </header>
        <Dashboard />
      </main>
    </div>
  )
}
