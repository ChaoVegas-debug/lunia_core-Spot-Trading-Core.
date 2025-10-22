import { GlassCard } from '../../components/UI/GlassCard';
import type { AdminOverviewResponse } from '../../types';
import { useAdminApi } from './useAdminApi';

export function AdminInfra() {
  const { data, loading, error, token } = useAdminApi<AdminOverviewResponse>('/api/v1/admin/overview');

  if (!token) {
    return <GlassCard title="Admin Token Required">Provide the admin token to view infra status.</GlassCard>;
  }

  const ops = (data?.state?.ops ?? {}) as Record<string, unknown>;
  const scheduler = (typeof ops.scheduler === 'object' && ops.scheduler !== null
    ? (ops.scheduler as Record<string, unknown>)
    : {}) as Record<string, unknown>;
  const sandbox = (typeof ops.sandbox === 'object' && ops.sandbox !== null
    ? (ops.sandbox as Record<string, unknown>)
    : {}) as Record<string, unknown>;
  const llm = (typeof ops.llm === 'object' && ops.llm !== null
    ? (ops.llm as Record<string, unknown>)
    : {}) as Record<string, unknown>;

  return (
    <GlassCard title="Infrastructure" subtitle="Scheduler, sandbox and feature flags">
      {loading && <p>Loading…</p>}
      {error && <p className="error-text">{error}</p>}
      <div className="flag-grid">
        <div className="flag-item">
          <span>Scheduler Enabled</span>
          <strong>{String(scheduler.enabled ?? false)}</strong>
        </div>
        <div className="flag-item">
          <span>Sandbox Mode</span>
          <strong>{String(sandbox.enabled ?? false)}</strong>
        </div>
        <div className="flag-item">
          <span>LLM Mode</span>
          <strong>{String(llm.mode ?? 'advice')}</strong>
        </div>
      </div>
      <p className="hint-text">Feature flags sync automatically with backend runtime state.</p>
    </GlassCard>
  );
}
