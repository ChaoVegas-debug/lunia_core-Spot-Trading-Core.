import { colors, radii, transitions } from '../../theme';
import './GlassCard.css';

interface GlassCardProps {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
  actions?: React.ReactNode;
}

export function GlassCard({ title, subtitle, children, actions }: GlassCardProps) {
  return (
    <section className="glass-card" style={{ borderRadius: radii.base, transition: transitions.default }}>
      <header className="glass-card__header">
        <div>
          <h3>{title}</h3>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions && <div className="glass-card__actions">{actions}</div>}
      </header>
      <div className="glass-card__content" style={{ color: colors.textPrimary }}>
        {children}
      </div>
    </section>
  );
}
