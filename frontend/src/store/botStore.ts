import { create } from 'zustand';

interface OpsStateResponse {
  auto_mode: boolean;
  global_stop: boolean;
  trading_on: boolean;
  agent_on: boolean;
  arb_on: boolean;
  sched_on: boolean;
  manual_override: boolean;
  manual_strategy: Record<string, unknown> | null;
  spot: Record<string, unknown>;
}

interface SpotRiskResponse {
  max_positions: number;
  max_trade_pct: number;
  risk_per_trade_pct: number;
  max_symbol_exposure_pct: number;
  tp_pct_default: number;
  sl_pct_default: number;
}

type BotMode = 'auto' | 'semi' | 'manual';

type RiskField = 'max_positions' | 'max_trade_pct' | 'max_symbol_exposure_pct';

interface BotState {
  loading: boolean;
  error: string | null;
  mode: BotMode;
  ops: OpsStateResponse | null;
  risk: SpotRiskResponse | null;
  riskDraft: Partial<Record<RiskField, number>>;
  updatingMode: boolean;
  updatingRisk: boolean;
  statusMessage: string | null;
  fetchAll: () => Promise<void>;
  setMode: (mode: BotMode) => Promise<void>;
  setRiskDraft: (field: RiskField, value: number) => void;
  resetRiskDraft: () => void;
  submitRisk: () => Promise<void>;
}

const API_BASE = '/api/v1';

const determineMode = (ops: OpsStateResponse | null): BotMode => {
  if (!ops) return 'auto';
  if (ops.manual_override) return 'manual';
  if (ops.auto_mode) return 'auto';
  return 'semi';
};

export const useBotStore = create<BotState>((set, get) => ({
  loading: true,
  error: null,
  mode: 'auto',
  ops: null,
  risk: null,
  riskDraft: {},
  updatingMode: false,
  updatingRisk: false,
  statusMessage: null,

  fetchAll: async () => {
    set({ loading: true, error: null });
    try {
      const [opsResp, riskResp] = await Promise.all([
        fetch(`${API_BASE}/ops/state`),
        fetch(`${API_BASE}/spot/risk`),
      ]);
      if (!opsResp.ok) {
        throw new Error(`Failed to load ops state (${opsResp.status})`);
      }
      if (!riskResp.ok) {
        throw new Error(`Failed to load risk state (${riskResp.status})`);
      }
      const ops = (await opsResp.json()) as OpsStateResponse;
      const risk = (await riskResp.json()) as SpotRiskResponse;
      set({
        ops,
        risk,
        riskDraft: {
          max_positions: risk.max_positions,
          max_trade_pct: Math.round(risk.max_trade_pct * 100),
          max_symbol_exposure_pct: Math.round(risk.max_symbol_exposure_pct * 100),
        },
        mode: determineMode(ops),
        loading: false,
        statusMessage: null,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to load bot state';
      set({ loading: false, error: message });
    }
  },

  setMode: async (mode) => {
    const { ops } = get();
    set({ updatingMode: true, error: null, statusMessage: null });
    try {
      if (mode === 'auto') {
        await fetch(`${API_BASE}/ops/auto_on`, { method: 'POST' });
        await fetch(`${API_BASE}/ops/state`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ manual_override: false, trading_on: true, agent_on: true }),
        });
      } else if (mode === 'semi') {
        await fetch(`${API_BASE}/ops/auto_off`, { method: 'POST' });
        await fetch(`${API_BASE}/ops/state`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ manual_override: false }),
        });
      } else {
        await fetch(`${API_BASE}/ops/auto_off`, { method: 'POST' });
        await fetch(`${API_BASE}/ops/state`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ manual_override: true, trading_on: true }),
        });
      }
      const response = await fetch(`${API_BASE}/ops/state`);
      if (!response.ok) {
        throw new Error(`Failed to refresh ops state (${response.status})`);
      }
      const nextOps = (await response.json()) as OpsStateResponse;
      set({ mode, ops: nextOps, updatingMode: false, statusMessage: 'Mode updated' });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update mode';
      set({ updatingMode: false, error: message, ops: ops ?? null });
    }
  },

  setRiskDraft: (field, value) => {
    set((state) => ({ riskDraft: { ...state.riskDraft, [field]: Number(value) } }));
  },

  resetRiskDraft: () => {
    const { risk } = get();
    if (!risk) return;
    set({
      riskDraft: {
        max_positions: risk.max_positions,
        max_trade_pct: Math.round(risk.max_trade_pct * 100),
        max_symbol_exposure_pct: Math.round(risk.max_symbol_exposure_pct * 100),
      },
    });
  },

  submitRisk: async () => {
    const { riskDraft } = get();
    set({ updatingRisk: true, error: null, statusMessage: null });
    try {
      const payload: Record<string, number> = {};
      if (typeof riskDraft.max_positions === 'number') {
        payload.max_positions = Math.max(1, Math.round(riskDraft.max_positions));
      }
      if (typeof riskDraft.max_trade_pct === 'number') {
        payload.max_trade_pct = Math.max(0, Number(riskDraft.max_trade_pct) / 100);
      }
      if (typeof riskDraft.max_symbol_exposure_pct === 'number') {
        payload.max_symbol_exposure_pct = Math.max(0, Number(riskDraft.max_symbol_exposure_pct) / 100);
      }
      await fetch(`${API_BASE}/spot/risk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const updatedRiskResp = await fetch(`${API_BASE}/spot/risk`);
      const risk = (await updatedRiskResp.json()) as SpotRiskResponse;
      set({
        risk,
        riskDraft: {
          max_positions: risk.max_positions,
          max_trade_pct: Math.round(risk.max_trade_pct * 100),
          max_symbol_exposure_pct: Math.round(risk.max_symbol_exposure_pct * 100),
        },
        updatingRisk: false,
        statusMessage: 'Risk settings updated',
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update risk settings';
      set({ updatingRisk: false, error: message });
    }
  },
}));
