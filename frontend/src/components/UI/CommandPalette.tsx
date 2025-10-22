import { useEffect, useMemo, useState } from 'react';
import { useStrategyStore } from '../../store/strategyStore';
import type { StrategyPreset } from '../../types';
import './CommandPalette.css';

interface CommandDefinition {
  id: string;
  label: string;
  hint: string;
  preset: StrategyPreset;
  overrides?: Record<string, number>;
  notes?: string;
  useOverrides?: boolean;
}

export function CommandPalette() {
  const previewPreset = useStrategyStore((s) => s.previewPreset);
  const setOverrides = useStrategyStore((s) => s.setOverrides);
  const resetOverrides = useStrategyStore((s) => s.resetOverrides);
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [highlighted, setHighlighted] = useState(0);
  const [busy, setBusy] = useState(false);

  const commands: CommandDefinition[] = useMemo(
    () => [
      {
        id: 'safe-today',
        label: 'Safe Today',
        hint: 'Preview conservative preset with defensive notes',
        preset: 'conservative',
        notes: 'Command palette — safe today focus',
        useOverrides: false,
      },
      {
        id: 'balanced-btc',
        label: 'Balanced for BTC',
        hint: 'Rebalance towards BTC-focused scalpers',
        preset: 'balanced',
        overrides: {
          micro_trend_scalper: 55,
          ema_rsi_trend: 25,
          scalping_breakout: 20,
        },
        notes: 'Command palette — BTC tilt',
        useOverrides: true,
      },
    ],
    []
  );

  const filtered = useMemo(() => {
    if (!query.trim()) {
      return commands;
    }
    const q = query.toLowerCase();
    return commands.filter((command) => command.label.toLowerCase().includes(q) || command.hint.toLowerCase().includes(q));
  }, [commands, query]);

  useEffect(() => {
    setHighlighted((index) => (filtered.length ? Math.min(index, filtered.length - 1) : 0));
  }, [filtered]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setIsOpen(true);
        setQuery('');
        setHighlighted(0);
        return;
      }
      if (event.key === 'Escape') {
        setIsOpen(false);
        return;
      }
      if (!isOpen) {
        return;
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setHighlighted((index) => (filtered.length ? (index + 1) % filtered.length : 0));
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setHighlighted((index) => (filtered.length ? (index - 1 + filtered.length) % filtered.length : 0));
      } else if (event.key === 'Enter') {
        event.preventDefault();
        if (filtered[highlighted]) {
          void runCommand(filtered[highlighted]);
        }
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [filtered, highlighted, isOpen]);

  const runCommand = async (command: CommandDefinition) => {
    if (busy) return;
    setBusy(true);
    try {
      if (command.overrides) {
        setOverrides(command.overrides);
      } else {
        resetOverrides();
      }
      await previewPreset(command.preset, {
        overrides: command.overrides,
        notes: command.notes,
        useOverrides: command.useOverrides,
      });
      setIsOpen(false);
    } finally {
      setBusy(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="command-backdrop" role="dialog" aria-modal="true">
      <div className="command-panel">
        <input
          autoFocus
          className="command-input"
          placeholder="Type a command…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <ul className="command-list">
          {filtered.length === 0 && <li className="command-empty">No matching commands.</li>}
          {filtered.map((command, index) => (
            <li key={command.id}>
              <button
                type="button"
                className={`command-item${index === highlighted ? ' active' : ''}`}
                onClick={() => void runCommand(command)}
                disabled={busy}
              >
                <div>
                  <div className="command-label">{command.label}</div>
                  <div className="command-hint">{command.hint}</div>
                </div>
                <span className="command-meta">↵</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
