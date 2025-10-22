import { GlassCard } from '../components/UI/GlassCard';
import './pages.css';

export default function Dashboard() {
  return (
    <div className="page-grid">
      <GlassCard title="Overview" subtitle="Realtime snapshot of Lunia Core">
        <p>Keep track of performance, balances and health across all orchestrated cores.</p>
      </GlassCard>
      <GlassCard title="Signals" subtitle="AI-driven sentiment">
        <ul>
          <li>Consensus confidence: 0.82</li>
          <li>Risk posture: Balanced</li>
          <li>Next review in 15 minutes</li>
        </ul>
      </GlassCard>
      <GlassCard title="Quick Actions">
        <div className="actions-row">
          <button type="button">Sync Signals</button>
          <button type="button">View Runbook</button>
          <button type="button">Trigger Smoke Test</button>
        </div>
      </GlassCard>
    </div>
  );
}
