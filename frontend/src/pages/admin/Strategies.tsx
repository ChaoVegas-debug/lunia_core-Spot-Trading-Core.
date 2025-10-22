import { useMemo } from 'react';

import { GlassCard } from '../../components/UI/GlassCard';
import type { AdminStrategyPerformanceResponse } from '../../types';
import { useAdminApi } from './useAdminApi';

export function AdminStrategies() {
  const { data, loading, error, token, refetch } = useAdminApi<AdminStrategyPerformanceResponse>(
    '/api/v1/admin/strategies/performance',
  );

  const items = useMemo(() => data?.items ?? [], [data]);

  if (!token) {
    return <GlassCard title="Admin Token Required">Provide the admin token to review strategies.</GlassCard>;
  }

  return (
    <GlassCard title="Strategy Performance" subtitle="Aggregated PnL & trade counts">
      {loading && <p>Loading…</p>}
      {error && <p className="error-text">{error}</p>}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Trades</th>
              <th>Total PnL</th>
              <th>Last Trade</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={4}>No strategy trades recorded.</td>
              </tr>
            )}
            {items.map((item) => (
              <tr key={item.strategy}>
                <td>{item.strategy}</td>
                <td>{item.trades}</td>
                <td>{item.total_pnl.toFixed(4)}</td>
                <td>{item.last_trade ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="actions-row">
        <button type="button" onClick={() => refetch()}>
          Refresh Metrics
        </button>
      </div>
    </GlassCard>
  );
}
