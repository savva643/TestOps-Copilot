import { ReactNode, createContext, useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useThemeConfig } from '@snack-uikit/utils'
import DefaultBrand from '@snack-uikit/figma-tokens/build/css/brand.module.css'
import { ButtonFilled } from '@snack-uikit/button'
import { getStoredCredentials } from '../api/auth'
import { MdLightMode, MdDarkMode } from 'react-icons/md'
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
  const navigate = useNavigate()
  const { theme, themeClassName, changeTheme } = useThemeConfig<Theme>({
    themeMap,
    defaultTheme: Theme.Light,
  })
  const themeModifier = theme === Theme.Dark ? 'theme-dark' : 'theme-light'
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    const credentials = getStoredCredentials()
    if (credentials) {
      setIsAuthenticated(true)
    } else {
      setIsAuthenticated(false)
    }
  }, [location.pathname])

  const navItems = [
    { id: 'dashboard', label: 'Дашборд', path: '/' },
    { id: 'generate', label: 'Генерация', path: '/generate' },
    { id: 'tasks', label: 'Задачи', path: '/tasks' },
    { id: 'optimize', label: 'Аналитика', path: '/optimize' },
  ]

  return (
    <ThemeContext.Provider value={{ theme, changeTheme }}>
      <div className={`layout ${themeClassName} ${themeModifier}`}>
        <header className="header">
          <div className="header-left">
            <div className="logo">
              <div className={`logo-mark ${theme === Theme.Dark ? 'logo-dark' : ''}`} />
              <span className="logo-text">TestOps Copilot</span>
            </div>
            <nav className="nav-links">
              {navItems.map((item) => {
                const active =
                  item.path === '/'
                    ? location.pathname === '/'
                    : location.pathname.startsWith(item.path)
                return (
                  <Link key={item.id} className={`nav-link ${active ? 'active' : ''}`} to={item.path}>
                    {item.label}
                  </Link>
                )
              })}
            </nav>
          </div>
          <div className="header-actions">
            {isAuthenticated ? (
              <ButtonFilled
                className="btn-primary"
                label="Профиль"
                size="s"
                onClick={() => navigate('/login')}
              />
            ) : (
              <ButtonFilled
                className="btn-primary"
                label="Войти"
                size="s"
                onClick={() => navigate('/login')}
              />
            )}
            <button
              className="theme-toggle-button"
              onClick={() => changeTheme(theme === Theme.Light ? Theme.Dark : Theme.Light)}
              aria-label={theme === Theme.Light ? 'Переключить на темную тему' : 'Переключить на светлую тему'}
            >
              {theme === Theme.Light ? (
                <MdDarkMode className="theme-icon" />
              ) : (
                <MdLightMode className="theme-icon" />
              )}
            </button>
          </div>
        </header>

        <main className="main-content">{children}</main>

        <footer className="footer">
          <p>TestOps Copilot · Cloud.ru · 2025</p>
        </footer>
      </div>
    </ThemeContext.Provider>
  )
}
