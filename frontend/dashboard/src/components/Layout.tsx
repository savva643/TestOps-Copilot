import { ReactNode, createContext, useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useThemeConfig } from '@snack-uikit/utils'
import DefaultBrand from '@snack-uikit/figma-tokens/build/css/brand.module.css'
import { ButtonFilled } from '@snack-uikit/button'
import { getStoredCredentials } from '../api/auth'
import { 
  MdLightMode, 
  MdDarkMode, 
  MdDashboard, 
  MdAddCircle, 
  MdAssignment, 
  MdAnalytics,
  MdPerson
} from 'react-icons/md'
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
  
  // Загружаем сохраненную тему из localStorage
  const getStoredTheme = (): Theme => {
    const stored = localStorage.getItem('testops-theme')
    return stored === Theme.Dark ? Theme.Dark : Theme.Light
  }
  
  const [storedTheme, setStoredTheme] = useState<Theme>(getStoredTheme())
  const { theme, themeClassName, changeTheme } = useThemeConfig<Theme>({
    themeMap,
    defaultTheme: storedTheme,
  })
  
  // Применяем сохраненную тему при первой загрузке
  useEffect(() => {
    const savedTheme = getStoredTheme()
    if (savedTheme !== theme) {
      changeTheme(savedTheme)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Только при монтировании
  
  // Сохраняем тему в localStorage при изменении
  useEffect(() => {
    if (theme !== storedTheme) {
      localStorage.setItem('testops-theme', theme)
      setStoredTheme(theme)
    }
  }, [theme])
  
  const themeModifier = theme === Theme.Dark ? 'theme-dark' : 'theme-light'
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const isLoginPage = location.pathname === '/login'

  useEffect(() => {
    const credentials = getStoredCredentials()
    if (credentials) {
      setIsAuthenticated(true)
    } else {
      setIsAuthenticated(false)
    }
  }, [location.pathname])

  const navItems = [
    { id: 'dashboard', label: 'Дашборд', path: '/', icon: MdDashboard },
    { id: 'generate', label: 'Генерация', path: '/generate', icon: MdAddCircle },
    { id: 'tasks', label: 'Задачи', path: '/tasks', icon: MdAssignment },
    { id: 'optimize', label: 'Аналитика', path: '/optimize', icon: MdAnalytics },
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
            {!isLoginPage && (
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
            )}
          </div>
          <div className="header-actions">
            {!isLoginPage && isAuthenticated && (
              <ButtonFilled
                className="btn-primary"
                label="Профиль"
                size="s"
                onClick={() => navigate('/login')}
              />
            )}
            {!isLoginPage && !isAuthenticated && (
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

        {/* Нижнее меню для мобильных устройств */}
        {!isLoginPage && (
          <nav className="bottom-nav">
            {navItems.map((item) => {
              const Icon = item.icon
              const active =
                item.path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.path)
              return (
                <Link 
                  key={item.id} 
                  className={`bottom-nav-item ${active ? 'active' : ''}`} 
                  to={item.path}
                  title={item.label}
                >
                  <Icon className="bottom-nav-icon" />
                  <span className="bottom-nav-label">{item.label}</span>
                </Link>
              )
            })}
            {isAuthenticated && (
              <Link 
                className={`bottom-nav-item ${location.pathname === '/login' ? 'active' : ''}`} 
                to="/login"
                title="Профиль"
              >
                <MdPerson className="bottom-nav-icon" />
                <span className="bottom-nav-label">Профиль</span>
              </Link>
            )}
          </nav>
        )}

        <footer className="footer">
          <p>TestOps Copilot · Cloud.ru · 2025</p>
        </footer>
      </div>
    </ThemeContext.Provider>
  )
}
