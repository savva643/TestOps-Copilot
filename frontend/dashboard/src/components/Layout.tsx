import { ReactNode, createContext } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useThemeConfig } from '@snack-uikit/utils'
import DefaultBrand from '@snack-uikit/figma-tokens/build/css/brand.module.css'
import { ButtonFilled } from '@snack-uikit/button'
import { Tabs } from '@snack-uikit/tabs'
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

  const navItems = [
    { id: 'dashboard', label: 'Дашборд', path: '/' },
    { id: 'generate', label: 'Генерация', path: '/generate' },
    { id: 'tasks', label: 'Задачи', path: '/tasks' },
    { id: 'optimize', label: 'Аналитика', path: '/optimize' },
  ]

  return (
    <ThemeContext.Provider value={{ theme, changeTheme }}>
      <div className={`layout ${themeClassName}`}>
        <header className="header">
          <div className="header-left">
            <div className="logo">TestOps Copilot</div>
            <Tabs
              size="s"
              value={
                navItems.find((item) => location.pathname.startsWith(item.path))?.id ??
                navItems[0].id
              }
              items={navItems.map((item) => ({
                id: item.id,
                label: <Link className="nav-link" to={item.path}>{item.label}</Link>,
              }))}
            />
          </div>
          <div className="header-actions">
            <ButtonFilled
              label={theme === Theme.Light ? 'Тёмная тема' : 'Светлая тема'}
              onClick={() => changeTheme(theme === Theme.Light ? Theme.Dark : Theme.Light)}
              size="s"
            />
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
