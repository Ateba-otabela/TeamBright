import { Outlet } from 'react-router-dom'

function RootLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <main id="main-content">
        <Outlet />
      </main>
    </div>
  )
}

export default RootLayout
