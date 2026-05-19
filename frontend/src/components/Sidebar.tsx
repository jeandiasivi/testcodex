const items = [
  'Recherche',
  'Lire',
  'Modifier',
  'Supprimer'
]

export function Sidebar() {
  return (
    <aside className="sidebar">
      <h2>Menu</h2>
      <nav>
        <ul>
          {items.map((item) => (
            <li key={item}>
              <button type="button">{item}</button>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}
