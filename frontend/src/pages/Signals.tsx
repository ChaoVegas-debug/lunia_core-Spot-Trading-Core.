import SignalCard from '../components/SignalCard/SignalCard';
import { GlassCard } from '../components/UI/GlassCard';
import { useApi } from '../hooks/useApi';
import { useFeatureFlags } from '../store/featureFlags';
import type { SignalItem } from '../types';
import './pages.css';

interface SignalSummary {
  total: number;
  confidence: number;
  top_pairs: string[];
}

export default function Signals() {
  const flags = useFeatureFlags();
  const { data: summary } = useApi<SignalSummary>('/api/v1/orchestrator/consensus', { skip: false });
  const {
    data: signals,
    loading: signalsLoading,
    error: signalsError,
  } = useApi<SignalItem[]>('/api/v1/signals?status=pending', { skip: false });

  const showExplainCards = flags.explainCardsV2 !== false;

  return (
    <div className="signals-page">
      <div className="page-grid">
        <GlassCard title="Signal Health" subtitle="Consensus output">
          {summary ? (
            <ul>
              <li>Total signals today: {summary.total}</li>
              <li>Average confidence: {(summary.confidence * 100).toFixed(1)}%</li>
              <li>Focus pairs: {summary.top_pairs.join(', ')}</li>
            </ul>
          ) : (
            <div className="empty-state">Fetching latest signals…</div>
          )}
        </GlassCard>
        <GlassCard title="LLM Insights">
          <p>Insights provided by the multi-model orchestrator appear here once available.</p>
        </GlassCard>
      </div>

      <section>
        <div className="section-header">
          <h2>Pending signals</h2>
          <p className="muted">Explain cards adapt for beginners, traders, and pro operators.</p>
        </div>
        {!showExplainCards && <div className="empty-state">Explain cards v2 disabled via feature flags.</div>}
        {showExplainCards && (
          <div className="signals-grid">
            {signalsLoading && <div className="empty-state">Loading signal cards…</div>}
            {signalsError && <div className="error-text">Unable to load signals: {signalsError.message}</div>}
            {!signalsLoading && !signalsError && (!signals || signals.length === 0) && (
              <div className="empty-state">No pending signals at the moment.</div>
            )}
            {!signalsLoading && !signalsError && signals &&
              signals.map((signal) => (
                <SignalCard
                  key={`${signal.symbol}-${signal.strategy}-${signal.generated_at}`}
                  signal={signal}
                  onExecute={() => console.info('Execute signal', signal)}
                  onDefer={() => console.info('Defer signal', signal)}
                  onDecline={() => console.info('Decline signal', signal)}
                  onExplainSimpler={() => console.info('Request simpler explanation', signal)}
                />
              ))}
          </div>
        )}
      </section>
    </div>
  );
}
