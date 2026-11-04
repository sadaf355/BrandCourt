import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../providers/ThemeProvider'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const next = theme === 'light' ? 'dark' : 'light'
  return (
    <button className="theme-toggle" type="button" onClick={toggleTheme} aria-label={`Switch to ${next} mode`} title={`Switch to ${next} mode`}>
      <span className="theme-toggle__icon" aria-hidden="true">{theme === 'light' ? <Moon size={17} /> : <Sun size={17} />}</span>
      <span className="theme-toggle__label">{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>
    </button>
  )
}
