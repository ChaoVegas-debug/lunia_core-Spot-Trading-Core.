import { useEffect, useMemo, useState } from 'react';
import { GlassCard } from '../components/UI/GlassCard';
import { useFeatureFlags } from '../store/featureFlags';
import { useFundsStore } from '../store/fundsStore';
import { PreviewDelta, PreviewDeltaEntry } from '../types';
import './pages.css';

const formatPercent = (value: number) => `${value.toFixed(0)}%`;

function DeltaList({
  delta,
}: {
  delta?: PreviewDelta;
}) {
  if (!delta || (Object.keys(delta).length === 0 && delta.constructor === Object)) {
    return <p>No material changes detected.</p>;
  }

  const renderEntry = (label: string, entry?: PreviewDeltaEntry) => {
    if (!entry) return null;
    const before = entry.before as { max_allocation_pct?: number; max_pct?: number } | undefined;
    const after = entry.after as { max_allocation_pct?: number; max_pct?: number } | undefined;
    const beforeValue = before?.max_allocation_pct ?? before?.max_pct ?? 0;
    const afterValue = after?.max_allocation_pct ?? after?.max_pct ?? 0;
    if (beforeValue === afterValue) return null;
    return (
      <li key={label}>
        <strong>{label}</strong>: {formatPercent(beforeValue)} → {formatPercent(afterValue)}
      </li>
    );
  };

  const exchangeDelta = delta.exchange_limits ? Object.entries(delta.exchange_limits) : [];

  return (
    <ul className="delta-list">
      {renderEntry('Global allocation', delta.global_limit)}
      {exchangeDelta.map(([exchange, entry]) => renderEntry(`${exchange} limit`, entry))}
    </ul>
  );
}

function PreviewModal({
  visible,
  onClose,
  onConfirm,
  preview,
}: {
  visible: boolean;
  onClose: () => void;
  onConfirm: () => void;
  preview: {
    expiresAt?: string;
    delta?: PreviewDelta;
  } | null;
}) {
  const [secondsLeft, setSecondsLeft] = useState<number>(() => {
    if (!preview?.expiresAt) return 0;
    return Math.max(0, Math.round((new Date(preview.expiresAt).getTime() - Date.now()) / 1000));
  });

  useEffect(() => {
    if (!preview?.expiresAt || !visible) {
      setSecondsLeft(0);
      return undefined;
    }
    const update = () => {
      const remaining = Math.max(0, Math.round((new Date(preview.expiresAt!).getTime() - Date.now()) / 1000));
      setSecondsLeft(remaining);
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [preview?.expiresAt, visible]);

  if (!visible || !preview) return null;

  return (
    <div className="preview-backdrop" role="dialog" aria-modal="true">
      <div className="preview-modal">
        <header className="preview-modal__header">
          <h3>Preview allocation changes</h3>
          {secondsLeft > 0 && <span className="preview-modal__timer">Expires in {secondsLeft}s</span>}
        </header>
        <div className="preview-modal__body">
          <p className="preview-modal__intro">Review the TL;DR before committing changes.</p>
          <DeltaList delta={preview.delta} />
        </div>
        <footer className="preview-modal__footer">
          <button className="btn-secondary" onClick={onClose} type="button">
            Cancel
          </button>
          <button onClick={onConfirm} type="button">
            Confirm changes
          </button>
        </footer>
      </div>
    </div>
  );
}

export default function FundsInWork() {
  const flags = useFeatureFlags();
  const fetchLimits = useFundsStore((state) => state.fetchLimits);
  const fetchBalances = useFundsStore((state) => state.fetchBalances);
  const teardown = useFundsStore((state) => state.teardown);
  const {
    loading,
    error,
    limits,
    working,
    preview,
    isPreviewVisible,
    balances,
    balancesLoading,
    undo,
    checkboxes,
    setGlobal,
    setExchange,
    setCheckbox,
    confirm,
    undoChange,
    dismissPreview,
  } = useFundsStore((state) => ({
    loading: state.loading,
    error: state.error,
    limits: state.limits,
    working: state.working,
    preview: state.preview,
    isPreviewVisible: state.isPreviewVisible,
    balances: state.balances,
    balancesLoading: state.balancesLoading,
    undo: state.undo,
    checkboxes: state.checkboxes,
    setGlobal: state.setGlobal,
    setExchange: state.setExchange,
    setCheckbox: state.setCheckbox,
    confirm: state.confirm,
    undoChange: state.undoChange,
    dismissPreview: state.dismissPreview,
  }));

  useEffect(() => {
    fetchLimits();
    fetchBalances();
    return () => {
      teardown();
    };
  }, [fetchLimits, fetchBalances, teardown]);

  const exchanges = useMemo(() => {
    if (!limits) return Object.keys(working.exchanges);
    const fromLimits = Object.keys(limits.exchanges ?? {});
    const fromWorking = Object.keys(working.exchanges);
    return Array.from(new Set([...fromLimits, ...fromWorking])).sort();
  }, [limits, working.exchanges]);

  const aggregatedBalances = balances?.aggregated ?? {};

  if (!flags.fundsLimits) {
    return (
      <div className="page-grid">
        <GlassCard title="Funds in Work" subtitle="Feature disabled">
          <p>Capital limits management is currently turned off via feature flags.</p>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="page-grid">
      <GlassCard title="Global allocation" subtitle="Define the maximum capital in work">
        {loading && <p className="muted">Loading limits…</p>}
        {error && <p className="error-text">{error}</p>}
        <div className="slider-row">
          <span>Global cap</span>
          <strong>{formatPercent(working.global)}</strong>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          value={working.global}
          onChange={(event) => setGlobal(Number(event.target.value))}
          className="funds-slider"
          aria-label="Global capital limit"
        />
        <div className="checkbox-group">
          <label>
            <input
              type="checkbox"
              checked={checkboxes.dontTouchStaking}
              onChange={(event) => setCheckbox('dontTouchStaking', event.target.checked)}
            />
            Don’t touch staking positions
          </label>
          <label>
            <input
              type="checkbox"
              checked={checkboxes.dontCancelLimitOrders}
              onChange={(event) => setCheckbox('dontCancelLimitOrders', event.target.checked)}
            />
            Don’t cancel existing limit orders
          </label>
          <label>
            <input
              type="checkbox"
              checked={checkboxes.autoConvertDust}
              onChange={(event) => setCheckbox('autoConvertDust', event.target.checked)}
            />
            Auto-convert dust to quote asset
          </label>
        </div>
        {undo && (
          <div className="undo-banner">
            <span>Undo available for {undo.secondsLeft}s</span>
            <button className="btn-secondary" type="button" onClick={undoChange}>
              Undo last change
            </button>
          </div>
        )}
      </GlassCard>

      <GlassCard title="Per-exchange limits" subtitle="Fine tune allocations by venue">
        {exchanges.length === 0 ? (
          <div className="empty-state">No exchange limits configured yet.</div>
        ) : (
          <table className="funds-table">
            <thead>
              <tr>
                <th>Exchange</th>
                <th>Allocation</th>
                <th className="numeric">Value</th>
              </tr>
            </thead>
            <tbody>
              {exchanges.map((exchange) => {
                const value = working.exchanges[exchange] ?? 0;
                return (
                  <tr key={exchange}>
                    <td>{exchange}</td>
                    <td>
                      <input
                        type="range"
                        min={0}
                        max={100}
                        value={value}
                        onChange={(event) => setExchange(exchange, Number(event.target.value))}
                        className="funds-slider"
                        aria-label={`${exchange} limit`}
                      />
                    </td>
                    <td className="numeric">{formatPercent(value)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </GlassCard>

      <GlassCard title="Balances snapshot" subtitle="Check aggregated assets across venues">
        <div className="balances-header">
          <button
            type="button"
            onClick={fetchBalances}
            className="btn-secondary"
            disabled={balancesLoading}
          >
            {balancesLoading ? 'Refreshing…' : 'Check balances'}
          </button>
          {balances?.timestamp && (
            <span className="muted">Updated {new Date(balances.timestamp).toLocaleTimeString()}</span>
          )}
        </div>
        {Object.keys(aggregatedBalances).length === 0 ? (
          <p className="muted">No balances available in the current session.</p>
        ) : (
          <table className="balances-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th className="numeric">Total</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(aggregatedBalances).map(([asset, info]) => (
                <tr key={asset}>
                  <td>{asset}</td>
                  <td className="numeric">{Number(info.total).toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </GlassCard>

      <PreviewModal
        visible={isPreviewVisible}
        preview={preview}
        onClose={dismissPreview}
        onConfirm={confirm}
      />
    </div>
  );
}
