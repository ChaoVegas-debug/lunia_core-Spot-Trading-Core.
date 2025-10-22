import { GlassCard } from '../components/UI/GlassCard';
import './pages.css';

export default function Portfolio() {
  return (
    <div className="page-grid">
      <GlassCard title="Portfolio Snapshot" subtitle="Positions & PnL">
        <div className="data-list">
          <div className="data-item">
            <strong>BTCUSDT</strong>
            <span>+4.2% · Unrealized $3,540</span>
          </div>
          <div className="data-item">
            <strong>ETHUSDT</strong>
            <span>+2.4% · Unrealized $1,120</span>
          </div>
        </div>
      </GlassCard>
      <GlassCard title="Explainability">
        <p>Cross-link with the backend explainability endpoint to surface decision context.</p>
      </GlassCard>
    </div>
  );
}
