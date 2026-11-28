import { Moon, Sun } from 'lucide-react';
import { useTheme } from './ThemeProvider';

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const next = theme === 'frost' ? 'Afterdark' : 'Frost';
  return (
    <button
      type="button"
      className="icon-button theme-toggle"
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next}`}
      onClick={toggle}
    >
      {theme === 'frost' ? <Moon size={19} /> : <Sun size={19} />}
    </button>
  );
}
