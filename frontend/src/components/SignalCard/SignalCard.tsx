import { useMemo, useState } from 'react';

import { GlassCard } from '../UI/GlassCard';

import type {
  AlternativeScenario,
  ExplanationLayer,
  ExplanationLayers,
  RiskMetrics,
  SignalItem,
} from '../../types';

import './SignalCard.css';

type LevelKey = 'beginner' | 'trader' | 'pro';

const LEVELS: Array<{ key: LevelKey; label: string }> = [
  { key: 'beginner', label: 'Beginner' },
  { key: 'trader', label: 'Trader' },
  { key: 'pro', label: 'Pro' },
];

interface SignalCardProps {
  signal: SignalItem;
  onExecute?: (signal: SignalItem) => void;
  onDefer?: (signal: SignalItem) => void;
  onDecline?: (signal: SignalItem) => void;
  onExplainSimpler?: (signal: SignalItem) => void;
}

function resolveLayer(layers: ExplanationLayers | undefined, key: LevelKey): ExplanationLayer | undefined {
  if (!layers) return undefined;
  return layers[key] ?? layers[LEVELS.find((entry) => entry.key === key)?.label?.toLowerCase() as LevelKey];
}

function renderRiskMetrics(metrics: RiskMetrics | undefined) {
  if (!metrics || Object.keys(metrics).length === 0) {
    return <p className="risk-empty">No risk metrics available.</p>;
  }
  return (
    <dl className="risk-grid">
      {Object.entries(metrics).map(([key, value]) => (
        <div key={key} className="risk-grid__item">
          <dt>{key.replace(/_/g, ' ')}</dt>
          <dd>{typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 4 }) : String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function renderScenarios(items: AlternativeScenario[] | undefined) {
  if (!items || items.length === 0) {
    return <p className="scenarios-empty">No alternative scenarios provided.</p>;
  }
  return (
    <ul className="scenarios-list">
      {items.map((scenario) => (
        <li key={scenario.label}>
          <div className="scenario-header">
            <span className="scenario-label">{scenario.label}</span>
            <span className="scenario-prob">{(scenario.probability * 100).toFixed(1)}%</span>
          </div>
          <p className="scenario-summary">{scenario.summary || 'No description provided.'}</p>
          <span className="scenario-action">Suggested action: {scenario.action}</span>
        </li>
      ))}
    </ul>
  );
}

export default function SignalCard({
  signal,
  onExecute,
  onDefer,
  onDecline,
  onExplainSimpler,
}: SignalCardProps) {
  const [activeLevel, setActiveLevel] = useState<LevelKey>('beginner');
  const layers = signal.explanation_layers;
  const layer = useMemo(() => resolveLayer(layers, activeLevel), [layers, activeLevel]);

  const certaintyPct = ((signal.certainty_score ?? 0) * 100).toFixed(1);
  const generatedAt = signal.generated_at ? new Date(signal.generated_at).toLocaleString() : 'unknown';

  const handle = (fn: ((s: SignalItem) => void) | undefined) => () => {
    if (fn) {
      fn(signal);
    }
  };

  return (
    <GlassCard
      title={`${signal.symbol} • ${signal.side}`}
      subtitle={`Strategy: ${signal.strategy ?? 'n/a'} • Certainty ${certaintyPct}% • Generated ${generatedAt}`}
      className="signal-card"
    >
      <div className="signal-card__content">
        <div className="signal-card__levels">
          <div className="level-tabs">
            {LEVELS.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                className={key === activeLevel ? 'active' : ''}
                onClick={() => setActiveLevel(key)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="level-body">
            {layer ? (
              <>
                <h4>{layer.title || LEVELS.find((entry) => entry.key === activeLevel)?.label}</h4>
                <p>{layer.summary}</p>
                {layer.bullets && layer.bullets.length > 0 && (
                  <ul className="level-bullets">
                    {layer.bullets.map((bullet) => (
                      <li key={bullet}>{bullet}</li>
                    ))}
                  </ul>
                )}
                {layer.details && (
                  <pre className="level-details">{JSON.stringify(layer.details, null, 2)}</pre>
                )}
              </>
            ) : (
              <p className="level-empty">Explanation unavailable for this level.</p>
            )}
          </div>
        </div>

        <div className="signal-card__aside">
          <section className="risk-section">
            <h4>Risk metrics</h4>
            {renderRiskMetrics(signal.risk_metrics)}
          </section>
          <section className="scenario-section">
            <h4>Alternative scenarios</h4>
            {renderScenarios(signal.alternative_scenarios)}
          </section>
        </div>
      </div>

      <div className="signal-card__cta">
        <button type="button" className="cta execute" onClick={handle(onExecute)}>
          Execute
        </button>
        <button type="button" className="cta defer" onClick={handle(onDefer)}>
          Defer
        </button>
        <button type="button" className="cta decline" onClick={handle(onDecline)}>
          Decline
        </button>
        <button type="button" className="cta explain" onClick={handle(onExplainSimpler)}>
          Explain simpler
        </button>
      </div>
    </GlassCard>
  );
}

