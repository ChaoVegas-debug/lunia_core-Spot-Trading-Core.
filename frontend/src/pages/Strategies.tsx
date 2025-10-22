import { useEffect, useMemo } from 'react';
import { GlassCard } from '../components/UI/GlassCard';
import { useStrategyStore } from '../store/strategyStore';
import type { StrategyPreset, StrategyChangeEntry } from '../types';
import './pages.css';

interface PresetCard {
  preset: StrategyPreset;
  title: string;
  description: string;
  notes?: string;
}

const PRESET_CARDS: PresetCard[] = [
  {
    preset: 'conservative',
    title: '🛡 Conservative',
    description: 'Capital preservation with mean reversion and hedged exposure.',
    notes: 'Safe today preset via dashboard',
  },
  {
    preset: 'balanced',
    title: '⚖ Balanced',
    description: 'Momentum and breakout blend with controlled leverage.',
  },
  {
    preset: 'aggressive',
    title: '🚀 Aggressive',
    description: 'High conviction scalps, volatility breakout and grid pilots.',
  },
];

const LONG_TERM_PACKS: PresetCard[] = [
  {
    preset: 'balanced',
    title: '🌍 Digital Gold Pack',
    description: 'BTC-heavy allocation with defensive hedges and carry.',
    notes: 'Long-term BTC focus',
  },
  {
    preset: 'conservative',
    title: '🏦 Yield Guardian',
    description: 'Stablecoin rotation + liquidity snipes, minimal drawdown.',
    notes: 'Yield guardian preset',
  },
  {
    preset: 'aggressive',
    title: '🌋 Growth Frontier',
    description: 'SOL/OP trend rides with adaptive grid light scalers.',
    notes: 'Growth frontier pack',
  },
];

const ASSET_OVERRIDE = [
  {
    asset: 'BTCUSDT',
    strategy: 'micro_trend_scalper',
    blurb: 'Micro trend capture on BTC core flows.',
  },
  {
    asset: 'ETHUSDT',
    strategy: 'ema_rsi_trend',
    blurb: 'Momentum follow-through with RSI guardrails.',
  },
  {
    asset: 'SOLUSDT',
    strategy: 'volatility_breakout',
    blurb: 'Solana breakout and reversal opportunities.',
  },
];

const numberFormatter = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const deltaFormatter = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

interface PreviewModalProps {
  expiresAt: string;
  strategy: string;
  explain?: { summary?: string; rationale?: string | null; confidence?: number; changes?: Array<{ strategy: string; before: number; after: number; delta: number; direction: string }>; };
  delta: Record<string, { before: number; after: number; delta: number; direction: string }>;
  onDismiss: () => void;
  onConfirm: () => void;
  loading: boolean;
}

function StrategyPreviewModal({ expiresAt, strategy, explain, delta, onDismiss, onConfirm, loading }: PreviewModalProps) {
  const expiry = useMemo(() => new Date(expiresAt), [expiresAt]);
  const timeRemaining = Math.max(0, Math.round((expiry.getTime() - Date.now()) / 1000));
  const entries = Object.entries(delta);
  return (
    <div className="preview-backdrop" role="dialog" aria-modal="true">
      <div className="preview-modal">
        <div className="preview-modal__header">
          <h3 className="preview-modal__intro">Preview — {strategy.toUpperCase()} mix</h3>
          <span className="preview-modal__timer">expires in ~{timeRemaining}s</span>
        </div>
        <div>
          <p className="muted">{explain?.summary ?? 'Review the allocation deltas before confirming.'}</p>
          {typeof explain?.confidence === 'number' && (
            <p className="muted">Confidence: {numberFormatter.format(explain.confidence)}</p>
          )}
        </div>
        <ul className="delta-list">
          {entries.length === 0 && <li>No allocation change detected.</li>}
          {entries.map(([name, info]) => (
            <li key={name}>
              <strong>{name}</strong>
              <div className="muted">
                {deltaFormatter.format(info.before)} → {deltaFormatter.format(info.after)}
                {' '}({info.direction === 'increase' ? '+' : ''}{deltaFormatter.format(info.delta)})
              </div>
            </li>
          ))}
        </ul>
        {explain?.rationale && <p className="muted">Why: {explain.rationale}</p>}
        <div className="preview-modal__footer">
          <button type="button" className="btn-secondary" onClick={onDismiss}>
            Dismiss
          </button>
          <button type="button" onClick={onConfirm} disabled={loading}>
            {loading ? 'Applying…' : 'Confirm strategy'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ChangeTimeline({ items }: { items: StrategyChangeEntry[] }) {
  if (!items.length) {
    return <div className="empty-state">No recent strategy changes yet.</div>;
  }
  return (
    <div className="data-list">
      {items.map((entry) => (
        <div key={entry.hash ?? entry.ts} className="data-item">
          <div>
            <strong>{entry.action.toUpperCase()}</strong>
            <div className="muted">{new Date(entry.ts).toLocaleString()}</div>
          </div>
          <div className="muted">{entry.actor}</div>
        </div>
      ))}
    </div>
  );
}

export default function Strategies() {
  const state = useStrategyStore((s) => ({
    loading: s.loading,
    error: s.error,
    statusMessage: s.statusMessage,
    current: s.current,
    overrides: s.overrides,
    preview: s.preview,
    previewLoading: s.previewLoading,
    confirmLoading: s.confirmLoading,
    undo: s.undo,
    changes: s.changes,
  }));
  const fetchCurrent = useStrategyStore((s) => s.fetchCurrent);
  const fetchChanges = useStrategyStore((s) => s.fetchChanges);
  const previewPreset = useStrategyStore((s) => s.previewPreset);
  const confirmPreview = useStrategyStore((s) => s.confirmPreview);
  const undoLast = useStrategyStore((s) => s.undoLast);
  const setOverride = useStrategyStore((s) => s.setOverride);
  const resetOverrides = useStrategyStore((s) => s.resetOverrides);
  const dismissPreview = useStrategyStore((s) => s.dismissPreview);

  useEffect(() => {
    void fetchCurrent();
    void fetchChanges();
  }, [fetchCurrent, fetchChanges]);

  const handlePreset = async (card: PresetCard) => {
    await previewPreset(card.preset, {
      notes: card.notes,
      useOverrides: false,
    });
  };

  const handleCustomPreview = async () => {
    await previewPreset('custom', { notes: 'Manual override preview', useOverrides: true });
  };

  const formatWeight = (weight: number | undefined) => numberFormatter.format((weight ?? 0) / 100);

  return (
    <div className="page-grid" style={{ alignItems: 'start' }}>
      <GlassCard title="Strategy presets" subtitle="One-click weighting profiles">
        <div className="data-list">
          {PRESET_CARDS.map((card) => (
            <div key={card.title} className="data-item" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '8px' }}>
              <div>
                <strong>{card.title}</strong>
                <p className="muted" style={{ margin: '6px 0 0' }}>{card.description}</p>
              </div>
              <div className="actions-row">
                <button type="button" disabled={state.previewLoading} onClick={() => handlePreset(card)}>
                  {state.previewLoading ? 'Loading…' : 'Preview'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard title="Long-term packs" subtitle="Curated allocations for macro regimes">
        <div className="data-list">
          {LONG_TERM_PACKS.map((card) => (
            <div key={card.title} className="data-item" style={{ flexDirection: 'column', gap: '8px', alignItems: 'flex-start' }}>
              <div>
                <strong>{card.title}</strong>
                <p className="muted" style={{ margin: '6px 0 0' }}>{card.description}</p>
              </div>
              <button type="button" className="btn-secondary" disabled={state.previewLoading} onClick={() => handlePreset(card)}>
                {state.previewLoading ? 'Loading…' : 'Preview pack'}
              </button>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard title="Per-asset overrides" subtitle="Fine tune weights before confirming">
        <div className="muted" style={{ marginBottom: '12px' }}>
          Adjust focus assets before generating a custom preview. Values represent share of capital per strategy.
        </div>
        {ASSET_OVERRIDE.map((item) => {
          const percent = state.overrides[item.strategy] ?? 0;
          return (
            <div key={item.strategy} style={{ marginBottom: '18px' }}>
              <div className="slider-row">
                <div>
                  <strong>{item.asset}</strong>
                  <div className="muted">{item.blurb}</div>
                </div>
                <span>{formatWeight(percent)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={percent}
                onChange={(event) => setOverride(item.strategy, Number(event.target.value))}
                className="funds-slider"
              />
            </div>
          );
        })}
        <div className="actions-row" style={{ marginTop: '16px' }}>
          <button type="button" onClick={handleCustomPreview} disabled={state.previewLoading}>
            {state.previewLoading ? 'Preparing…' : 'Preview custom mix'}
          </button>
          <button type="button" className="btn-secondary" onClick={resetOverrides}>
            Reset overrides
          </button>
        </div>
      </GlassCard>

      <GlassCard title="Current allocation" subtitle="Live spot core weights">
        {state.current ? (
          <table className="funds-table">
            <thead>
              <tr>
                <th>Strategy</th>
                <th className="numeric">Weight</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(state.current.weights).map(([name, weight]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td className="numeric">{numberFormatter.format(weight)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="muted">Loading current weights…</div>
        )}
        {state.statusMessage && <div className="muted" style={{ marginTop: '12px' }}>{state.statusMessage}</div>}
        {state.error && <div className="error-text">{state.error}</div>}
        {state.undo && (
          <div className="undo-banner">
            <span>Undo available for {state.undo.secondsLeft}s</span>
            <button type="button" className="btn-secondary" onClick={undoLast} disabled={state.confirmLoading}>
              Undo change
            </button>
          </div>
        )}
      </GlassCard>

      <GlassCard title="Recent changes" subtitle="Latest strategy events">
        <ChangeTimeline items={state.changes} />
      </GlassCard>

      {state.preview && (
        <StrategyPreviewModal
          expiresAt={state.preview.expiresAt}
          strategy={state.preview.strategy}
          explain={state.preview.explain}
          delta={state.preview.delta}
          onDismiss={dismissPreview}
          onConfirm={confirmPreview}
          loading={state.confirmLoading}
        />
      )}
    </div>
  );
}
