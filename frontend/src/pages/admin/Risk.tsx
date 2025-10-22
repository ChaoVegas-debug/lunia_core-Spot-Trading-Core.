import { GlassCard } from '../../components/UI/GlassCard';
import type { AdminOverviewResponse } from '../../types';
import { useAdminApi } from './useAdminApi';

export function AdminRisk() {
  const { data, loading, error, token, refetch } = useAdminApi<AdminOverviewResponse>('/api/v1/admin/overview');

  if (!token) {
    return <GlassCard title="Admin Token Required">Provide the admin token to audit risk settings.</GlassCard>;
  }

  const ops = (data?.state?.ops ?? {}) as Record<string, unknown>;
  const capital = (typeof ops.capital === 'object' && ops.capital !== null
    ? (ops.capital as Record<string, unknown>)
    : {}) as Record<string, unknown>;
  const reserves = (typeof ops.reserves === 'object' && ops.reserves !== null
    ? (ops.reserves as Record<string, unknown>)
    : {}) as Record<string, unknown>;

  return (
    <GlassCard title="Risk & Capital" subtitle="Ops state extracted from runtime">
      {loading && <p>Loading…</p>}
      {error && <p className="error-text">{error}</p>}
      <div className="grid-two">
        <div>
          <h4>Capital Configuration</h4>
          <ul>
            <li>Cap %: {String(capital.cap_pct ?? '—')}</li>
            <li>Hard Max %: {String(capital.hard_max_pct ?? '—')}</li>
            <li>Portfolio reserve: {String(reserves.portfolio ?? '—')}</li>
            <li>Arbitrage reserve: {String(reserves.arbitrage ?? '—')}</li>
          </ul>
        </div>
        <div>
          <h4>Spot Weights</h4>
          <pre className="json-preview">{JSON.stringify(((data?.state?.spot as Record<string, unknown>)?.weights ?? {}), null, 2)}</pre>
        </div>
      </div>
      <div className="actions-row">
        <button type="button" onClick={() => refetch()}>Refresh Snapshot</button>
      </div>
    </GlassCard>
  );
}
