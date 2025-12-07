import { ReactNode, createContext, useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useThemeConfig } from '@snack-uikit/utils'
import DefaultBrand from '@snack-uikit/figma-tokens/build/css/brand.module.css'
import { ButtonFilled } from '@snack-uikit/button'
import './Layout.css'

export enum Theme {
  Light = 'Light',
  Dark = 'Dark',
}

const themeMap = {
  [Theme.Light]: DefaultBrand.light,
  [Theme.Dark]: DefaultBrand.dark,
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
  const { theme, themeClassName, changeTheme } = useThemeConfig<Theme>({
    themeMap,
    defaultTheme: Theme.Light,
  })

  // Apply theme class to body
  useEffect(() => {
    document.body.className = themeClassName
    return () => {
      document.body.className = ''
    }
  }, [themeClassName])

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
            <div className="theme-toggle">
              <ButtonFilled
                label={theme === Theme.Light ? '🌙' : '☀️'}
                onClick={() => changeTheme(theme === Theme.Light ? Theme.Dark : Theme.Light)}
                size="s"
              />
            </div>
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
