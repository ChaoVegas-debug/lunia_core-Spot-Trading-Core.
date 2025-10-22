import { GlassCard } from '../../components/UI/GlassCard';
import { useAdminApi } from './useAdminApi';
import type { AdminOverviewResponse } from '../../types';

export function AdminOverview() {
  const { data, loading, error, token, refetch } = useAdminApi<AdminOverviewResponse>('/api/v1/admin/overview');

  if (!token) {
    return <GlassCard title="Admin Token Required">Provide the admin token to view overview data.</GlassCard>;
  }

  return (
    <GlassCard title="Operational Overview" subtitle="Spot runtime state & funds limits">
      {loading && <p>Loading…</p>}
      {error && <p className="error-text">{error}</p>}
      {data && (
        <div className="admin-overview-grid">
          {(() => {
            const spot = (data.state?.spot ?? {}) as Record<string, unknown>;
            const weights = (spot.weights as Record<string, unknown>) ?? {};
            return (
              <div>
                <h4>Spot Weights</h4>
                <pre className="json-preview">{JSON.stringify(weights, null, 2)}</pre>
              </div>
            );
          })()}
          <div>
            <h4>Runtime Flags</h4>
            <ul>
              <li>Auto mode: {String(data.state?.auto_mode ?? false)}</li>
              <li>Global stop: {String(data.state?.global_stop ?? false)}</li>
            </ul>
          </div>
          {(() => {
            const pending = data.funds.pending;
            return (
              <div>
                <h4>Funds</h4>
                <pre className="json-preview">{JSON.stringify(data.funds.limits, null, 2)}</pre>
                {pending && (
                  <p className="pending-text">Pending preview expires soon. Review before confirm.</p>
                )}
              </div>
            );
          })()}
          <div>
            <h4>Recent Strategy Changes</h4>
            <ul className="change-list">
              {data.recent_strategy_changes.length === 0 && <li>No changes recorded</li>}
              {data.recent_strategy_changes.map((change, index) => {
                const record = (change ?? {}) as Record<string, unknown>;
                const action = typeof record.action === 'string' ? record.action : 'change';
                const ts = typeof record.ts === 'string' ? record.ts : 'unknown';
                return (
                  <li key={index}>
                    <strong>{action}</strong> ·<span>{ts}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
      <div className="actions-row">
        <button type="button" onClick={() => refetch()}>
          Refresh Overview
        </button>
      </div>
    </GlassCard>
  );
}
