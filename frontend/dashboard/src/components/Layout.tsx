import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Layout.css'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <div className="layout">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <h1>TestOps Copilot</h1>
          </div>
          <nav className="nav">
            <Link
              to="/"
              className={`nav-link ${isActive('/') ? 'active' : ''}`}
            >
              Home
            </Link>
            <Link
              to="/generate"
              className={`nav-link ${isActive('/generate') ? 'active' : ''}`}
            >
              Generate Tests
            </Link>
            <Link
              to="/tasks"
              className={`nav-link ${isActive('/tasks') ? 'active' : ''}`}
            >
              Tasks
            </Link>
            <Link
              to="/optimize"
              className={`nav-link ${isActive('/optimize') ? 'active' : ''}`}
            >
              Optimize
            </Link>
          </nav>
        </div>
      </header>
      <main className="main-content">{children}</main>
      <footer className="footer">
        <p>TestOps Copilot © 2024 Cloud.ru</p>
      </footer>
    </div>
  )
}
