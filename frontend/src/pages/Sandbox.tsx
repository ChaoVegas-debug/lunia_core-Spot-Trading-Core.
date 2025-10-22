import { FormEvent, useMemo, useState } from 'react';

import { GlassCard } from '../components/UI/GlassCard';
import { useSandboxStore } from '../store/sandboxStore';
import { SandboxResult } from '../types';
import './pages.css';

const STRATEGY_OPTIONS = [
  { label: '🛡 Conservative', value: 'conservative' },
  { label: '⚖ Balanced', value: 'balanced' },
  { label: '🚀 Aggressive', value: 'aggressive' },
];

interface FormState {
  strategy: string;
  days: number;
  initialCapital: number;
}

const DEFAULT_FORM: FormState = {
  strategy: 'conservative',
  days: 30,
  initialCapital: 10_000,
};

function EquityChart({ result }: { result: SandboxResult }) {
  const path = useMemo(() => {
    if (!result.equity_curve.length) return '';
    const values = result.equity_curve.map((point) => point.equity);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    return result.equity_curve
      .map((point, index) => {
        const x = (index / Math.max(1, result.equity_curve.length - 1)) * 100;
        const y = 100 - ((point.equity - min) / range) * 100;
        return `${index === 0 ? 'M' : 'L'}${x},${y}`;
      })
      .join(' ');
  }, [result]);

  return (
    <svg className="equity-chart" viewBox="0 0 100 100" preserveAspectRatio="none">
      <path d={path} fill="none" stroke="url(#equityGradient)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      <defs>
        <linearGradient id="equityGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#a855f7" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export default function Sandbox() {
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const { job, submitting, error, run, reset } = useSandboxStore();

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await run({
      strategy: form.strategy,
      days: form.days,
      initial_capital: form.initialCapital,
    });
  };

  const handleReset = () => {
    setForm(DEFAULT_FORM);
    reset();
  };

  const result = job?.result;

  return (
    <div className="page-grid">
      <GlassCard title="Strategy Sandbox" subtitle="Backtest strategies safely before live deployment">
        <form className="form-grid" onSubmit={handleSubmit}>
          <label htmlFor="sandbox-strategy">Strategy preset</label>
          <select
            id="sandbox-strategy"
            value={form.strategy}
            onChange={(event) => setForm((prev) => ({ ...prev, strategy: event.target.value }))}
          >
            {STRATEGY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>

          <label htmlFor="sandbox-days">Lookback (days)</label>
          <input
            id="sandbox-days"
            type="number"
            min={5}
            max={365}
            value={form.days}
            onChange={(event) => setForm((prev) => ({ ...prev, days: Number(event.target.value) }))}
          />

          <label htmlFor="sandbox-capital">Initial capital (USD)</label>
          <input
            id="sandbox-capital"
            type="number"
            min={1000}
            step={500}
            value={form.initialCapital}
            onChange={(event) => setForm((prev) => ({ ...prev, initialCapital: Number(event.target.value) }))}
          />

          <div className="form-actions">
            <button type="submit" disabled={submitting}>
              {submitting ? 'Running…' : 'Run Backtest'}
            </button>
            <button type="button" className="secondary" onClick={handleReset}>
              Reset
            </button>
          </div>
        </form>
        {error && <div className="error-banner">{error}</div>}
        {job && !result && (
          <div className="status-banner">
            <strong>Job status:</strong> {job.status.toUpperCase()} • tracking {job.job_id.slice(0, 8)}
          </div>
        )}
      </GlassCard>

      {result && (
        <GlassCard title="Backtest Results" subtitle={`Sharpe ${result.metrics.sharpe_ratio.toFixed(2)}`}>
          <div className="result-layout">
            <div className="chart-container">
              <EquityChart result={result} />
            </div>
            <div className="metrics-grid">
              <div>
                <span className="metric-label">PnL %</span>
                <span className="metric-value">{result.metrics.total_return_pct.toFixed(2)}%</span>
              </div>
              <div>
                <span className="metric-label">Win rate</span>
                <span className="metric-value">{result.metrics.win_rate.toFixed(1)}%</span>
              </div>
              <div>
                <span className="metric-label">Max drawdown</span>
                <span className="metric-value">{result.metrics.max_drawdown_pct.toFixed(2)}%</span>
              </div>
              <div>
                <span className="metric-label">Latency</span>
                <span className="metric-value">{result.metrics.average_latency_ms.toFixed(1)} ms</span>
              </div>
              <div>
                <span className="metric-label">Slippage</span>
                <span className="metric-value">{result.metrics.average_slippage_bps.toFixed(1)} bps</span>
              </div>
            </div>
          </div>
          <div className="trades-table">
            <header>
              <span>Day</span>
              <span>Price</span>
              <span>PnL %</span>
            </header>
            {result.trades.map((trade) => (
              <div key={trade.day}>
                <span>{trade.day}</span>
                <span>${trade.price.toFixed(2)}</span>
                <span className={trade.pnl_pct >= 0 ? 'positive' : 'negative'}>
                  {trade.pnl_pct.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </GlassCard>
      )}
    </div>
  );
}
