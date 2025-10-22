import { GlassCard } from '../../components/UI/GlassCard';

export function AdminMarketing() {
  return (
    <GlassCard title="Marketing Signals" subtitle="Human-readable highlights for stakeholders">
      <p>
        Use this space to summarise strategy performance, publish marketing-safe stats and craft updates for
        external stakeholders. Future iterations can hydrate this view from analytics pipelines.
      </p>
      <ul>
        <li>Share latest Sharpe / hit-rate with compliance-approved formatting.</li>
        <li>Summarise new features shipped to Telegram or dashboard.</li>
        <li>Highlight risk posture changes in plain language for customer success teams.</li>
      </ul>
    </GlassCard>
  );
}
