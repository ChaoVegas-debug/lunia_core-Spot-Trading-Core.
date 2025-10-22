import { useEffect } from 'react';
import { GlassCard } from '../components/UI/GlassCard';
import { useBotStore } from '../store/botStore';
import './pages.css';

const modeOptions: Array<{ value: 'auto' | 'semi' | 'manual'; label: string; helper: string }> = [
  { value: 'auto', label: 'Auto', helper: 'Supervisor orchestrates entries and exits end-to-end.' },
  { value: 'semi', label: 'Semi-Auto', helper: 'Signals generated automatically, manual confirmation required.' },
  { value: 'manual', label: 'Manual', helper: 'Human override — AI muted, trading kept on standby.' },
];

export default function BotControl() {
  const state = useBotStore((s) => ({
    loading: s.loading,
    error: s.error,
    mode: s.mode,
    ops: s.ops,
    riskDraft: s.riskDraft,
    updatingMode: s.updatingMode,
    updatingRisk: s.updatingRisk,
    statusMessage: s.statusMessage,
  }));
  const fetchAll = useBotStore((s) => s.fetchAll);
  const setMode = useBotStore((s) => s.setMode);
  const setRiskDraft = useBotStore((s) => s.setRiskDraft);
  const submitRisk = useBotStore((s) => s.submitRisk);
  const resetRiskDraft = useBotStore((s) => s.resetRiskDraft);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  const handleModeChange = async (value: 'auto' | 'semi' | 'manual') => {
    await setMode(value);
  };

  const formatPercent = (value?: number) => {
    if (typeof value !== 'number') return '—';
    return `${value}%`;
  };

  return (
    <div className="page-grid" style={{ alignItems: 'start' }}>
      <GlassCard title="Bot execution mode" subtitle="Choose how the orchestrator operates">
        <div className="data-list">
          {modeOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`mode-option${state.mode === option.value ? ' active' : ''}`}
              onClick={() => handleModeChange(option.value)}
              disabled={state.updatingMode}
            >
              <strong>{option.label}</strong>
              <span className="muted">{option.helper}</span>
            </button>
          ))}
        </div>
        {state.statusMessage && <p className="muted" style={{ marginTop: '12px' }}>{state.statusMessage}</p>}
        {state.error && <p className="error-text">{state.error}</p>}
      </GlassCard>

      <GlassCard title="Risk guardrails" subtitle="Key limits for automated execution">
        <div className="data-list">
          <label className="slider-row" htmlFor="maxDrawdown">
            <div>
              <strong>Per-asset drawdown cap</strong>
              <div className="muted">Max exposure per symbol before cut</div>
            </div>
            <span>{formatPercent(state.riskDraft.max_symbol_exposure_pct)}</span>
          </label>
          <input
            id="maxDrawdown"
            type="range"
            min={5}
            max={100}
            value={state.riskDraft.max_symbol_exposure_pct ?? 35}
            onChange={(event) => setRiskDraft('max_symbol_exposure_pct', Number(event.target.value))}
            className="funds-slider"
          />

          <label className="slider-row" htmlFor="portfolioStop">
            <div>
              <strong>Portfolio stop</strong>
              <div className="muted">% equity allowed per trade</div>
            </div>
            <span>{formatPercent(state.riskDraft.max_trade_pct)}</span>
          </label>
          <input
            id="portfolioStop"
            type="range"
            min={1}
            max={100}
            value={state.riskDraft.max_trade_pct ?? 20}
            onChange={(event) => setRiskDraft('max_trade_pct', Number(event.target.value))}
            className="funds-slider"
          />

          <label className="slider-row" htmlFor="maxPositions">
            <div>
              <strong>Max concurrent positions</strong>
              <div className="muted">How many strategies may run simultaneously</div>
            </div>
            <span>{state.riskDraft.max_positions ?? '—'}</span>
          </label>
          <input
            id="maxPositions"
            type="range"
            min={1}
            max={12}
            value={state.riskDraft.max_positions ?? 5}
            onChange={(event) => setRiskDraft('max_positions', Number(event.target.value))}
            className="funds-slider"
          />
        </div>
        <div className="actions-row" style={{ marginTop: '16px' }}>
          <button type="button" onClick={submitRisk} disabled={state.updatingRisk}>
            {state.updatingRisk ? 'Saving…' : 'Apply limits'}
          </button>
          <button type="button" className="btn-secondary" onClick={resetRiskDraft}>
            Reset
          </button>
        </div>
      </GlassCard>

      <GlassCard title="Runtime snapshot" subtitle="Operational indicators">
        {state.loading && <div className="muted">Loading bot state…</div>}
        {!state.loading && state.ops && (
          <div className="data-list">
            <div className="data-item">
              <strong>Auto mode</strong>
              <span>{state.ops.auto_mode ? 'Enabled' : 'Disabled'}</span>
            </div>
            <div className="data-item">
              <strong>Manual override</strong>
              <span>{state.ops.manual_override ? 'Active' : 'Inactive'}</span>
            </div>
            <div className="data-item">
              <strong>Trading services</strong>
              <span>{state.ops.trading_on ? 'ON' : 'OFF'}</span>
            </div>
            <div className="data-item">
              <strong>Scheduler</strong>
              <span>{state.ops.sched_on ? 'ON' : 'OFF'}</span>
            </div>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
