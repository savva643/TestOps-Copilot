import { ReactNode, createContext, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Layout.css'

export enum Theme {
  Light = 'Light',
  Dark = 'Dark',
}

// Temporary theme implementation until snack-uikit packages are properly installed
const getThemeClassName = (theme: Theme): string => {
  return theme === Theme.Dark ? 'dark' : 'light'
}

type ThemeContextProps = {
  theme: Theme
  changeTheme(value: Theme): void
}

export const ThemeContext = createContext<ThemeContextProps>({
  theme: Theme.Light,
  changeTheme() {},
})

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const [theme, setTheme] = useState<Theme>(Theme.Light)
  const themeClassName = getThemeClassName(theme)
  const changeTheme = (newTheme: Theme) => setTheme(newTheme)

  const isActive = (path: string) => location.pathname === path

  return (
    <ThemeContext.Provider value={{ theme, changeTheme }}>
      <div className={`layout ${themeClassName}`}>
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
    </ThemeContext.Provider>
  )
}
