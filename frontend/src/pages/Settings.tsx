import { GlassCard } from '../components/UI/GlassCard';
import { useFeatureFlags } from '../store/featureFlags';
import './pages.css';

export default function Settings() {
  const flags = useFeatureFlags();

  return (
    <div className="page-grid">
      <GlassCard title="Feature Flags" subtitle="Runtime toggles">
        <ul>
          <li>Manual mode: {flags.manualMode ? 'enabled' : 'disabled'}</li>
          <li>Explain cards v2: {flags.explainCardsV2 ? 'enabled' : 'disabled'}</li>
          <li>Funds limits: {flags.fundsLimits ? 'enabled' : 'disabled'}</li>
          <li>Sandbox: {flags.isSandboxEnabled ? 'enabled' : 'disabled'}</li>
          <li>Scheduler: {flags.scheduler ? 'enabled' : 'disabled'}</li>
        </ul>
      </GlassCard>
      <GlassCard title="Theme">
        <p>The dashboard uses a glassmorphism dark theme with Lunia Core accent palette.</p>
      </GlassCard>
    </div>
  );
}
