import { NavLink } from 'react-router-dom';
import { CommandPalette } from '../UI/CommandPalette';
import { colors, radii, transitions } from '../../theme';
import './Layout.css';

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/funds', label: 'Funds in Work' },
  { to: '/strategies', label: 'Strategies' },
  { to: '/sandbox', label: 'Sandbox' },
  { to: '/portfolio', label: 'Portfolio' },
  { to: '/signals', label: 'Signals' },
  { to: '/bot', label: 'Bot Control' },
  { to: '/admin', label: 'Admin' },
  { to: '/settings', label: 'Settings' },
];

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout" style={{ backgroundColor: colors.background }}>
      <aside className="sidebar">
        <div className="brand">Lunia Core</div>
        <nav>
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content" style={{ borderRadius: radii.base, transition: transitions.default }}>
        {children}
      </main>
      <CommandPalette />
    </div>
  );
}
