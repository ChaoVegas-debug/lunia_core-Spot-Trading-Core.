import { create } from 'zustand';
import type {
  StrategyChangeEntry,
  StrategyConfirmResponse,
  StrategyPreset,
  StrategyPreviewExplain,
  StrategyPreviewResponse,
  StrategyUndoResponse,
  StrategyWeightsState,
} from '../types';

const API_BASE = '/api/v1';
const TTL_BUFFER_MS = 500; // buffer to clear preview slightly after expiry

interface PreviewState {
  id: string;
  strategy: StrategyPreset;
  expiresAt: string;
  delta: StrategyPreviewResponse['delta'];
  explain?: StrategyPreviewExplain;
  weights: Record<string, number>;
}

interface UndoState {
  token: string;
  expiresAt: string;
  secondsLeft: number;
}

interface StrategyState {
  loading: boolean;
  error: string | null;
  statusMessage: string | null;
  current: StrategyWeightsState | null;
  overrides: Record<string, number>; // percentage values 0-100
  preview: PreviewState | null;
  previewLoading: boolean;
  confirmLoading: boolean;
  undo: UndoState | null;
  changes: StrategyChangeEntry[];
  fetchCurrent: () => Promise<void>;
  fetchChanges: () => Promise<void>;
  setOverride: (strategy: string, percent: number) => void;
  setOverrides: (overrides: Record<string, number>) => void;
  resetOverrides: () => void;
  previewPreset: (
    preset: StrategyPreset,
    options?: { notes?: string; overrides?: Record<string, number>; useOverrides?: boolean }
  ) => Promise<void>;
  confirmPreview: () => Promise<void>;
  undoLast: () => Promise<void>;
  dismissPreview: () => void;
}

const clampPercent = (value: number) => {
  if (Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
};

const toPercentMap = (weights: Record<string, number>) => {
  const result: Record<string, number> = {};
  for (const [name, weight] of Object.entries(weights)) {
    result[name] = clampPercent(weight * 100);
  }
  return result;
};

const toWeightMap = (percentages: Record<string, number>) => {
  const result: Record<string, number> = {};
  for (const [name, percent] of Object.entries(percentages)) {
    if (percent <= 0) continue;
    result[name] = Number((percent / 100).toFixed(4));
  }
  return result;
};

export const useStrategyStore = create<StrategyState>((set, get) => {
  let previewTimeout: ReturnType<typeof setTimeout> | null = null;
  let undoInterval: ReturnType<typeof setInterval> | null = null;

  const clearPreviewTimeout = () => {
    if (previewTimeout) {
      clearTimeout(previewTimeout);
      previewTimeout = null;
    }
  };

  const clearUndoInterval = () => {
    if (undoInterval) {
      clearInterval(undoInterval);
      undoInterval = null;
    }
  };

  const schedulePreviewExpiry = (expiresAt: string) => {
    clearPreviewTimeout();
    const target = new Date(expiresAt).getTime();
    const delay = Math.max(0, target - Date.now() + TTL_BUFFER_MS);
    previewTimeout = setTimeout(() => {
      set((state) => ({
        preview: null,
        statusMessage: state.statusMessage,
        error: state.error,
      }));
    }, delay);
  };

  const startUndoCountdown = (token: string, expiresAt: string) => {
    clearUndoInterval();
    const computeSeconds = () => Math.max(0, Math.round((new Date(expiresAt).getTime() - Date.now()) / 1000));

    const tick = () => {
      const secondsLeft = computeSeconds();
      set((state) => ({
        undo: secondsLeft > 0 ? { token, expiresAt, secondsLeft } : null,
        statusMessage: state.statusMessage,
        error: state.error,
      }));
      if (secondsLeft <= 0) {
        clearUndoInterval();
      }
    };

    tick();
    undoInterval = setInterval(tick, 1000);
  };

  const refreshWeightsFromResponse = (weights: Record<string, number>) => {
    const enabled = get().current?.enabled ?? true;
    set({
      current: { enabled, weights },
      overrides: toPercentMap(weights),
    });
  };

  return {
    loading: false,
    error: null,
    statusMessage: null,
    current: null,
    overrides: {},
    preview: null,
    previewLoading: false,
    confirmLoading: false,
    undo: null,
    changes: [],

    fetchCurrent: async () => {
      set({ loading: true, error: null });
      try {
        const response = await fetch(`${API_BASE}/spot/strategies`);
        if (!response.ok) {
          throw new Error(`Failed to load strategies (${response.status})`);
        }
        const data = (await response.json()) as StrategyWeightsState;
        set({
          current: data,
          overrides: toPercentMap(data.weights ?? {}),
          loading: false,
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to load strategies';
        set({ loading: false, error: message });
      }
    },

    fetchChanges: async () => {
      try {
        const response = await fetch(`${API_BASE}/portfolio/changes?limit=8`);
        if (!response.ok) {
          throw new Error('failed to fetch changes');
        }
        const payload = (await response.json()) as { changes: StrategyChangeEntry[] };
        set({ changes: payload.changes ?? [] });
      } catch {
        // silent fail for changelog
      }
    },

    setOverride: (strategy, percent) => {
      set((state) => ({
        overrides: { ...state.overrides, [strategy]: clampPercent(percent) },
      }));
    },

    setOverrides: (overrides) => {
      const next: Record<string, number> = {};
      for (const [key, value] of Object.entries(overrides)) {
        next[key] = clampPercent(value);
      }
      set({ overrides: next });
    },

    resetOverrides: () => {
      const { current } = get();
      if (!current) return;
      set({ overrides: toPercentMap(current.weights ?? {}) });
    },

    previewPreset: async (preset, options) => {
      set({ previewLoading: true, error: null, statusMessage: null });
      try {
        const state = get();
        const overridesSource = options?.overrides ?? state.overrides;
        const shouldApplyOverrides = options?.useOverrides ?? preset === 'custom';
        const payload: Record<string, unknown> = {
          strategy: preset,
        };
        const weights = shouldApplyOverrides ? toWeightMap(overridesSource) : {};
        if (Object.keys(weights).length > 0) {
          payload.weights = weights;
        }
        if (options?.notes) {
          payload.notes = options.notes;
        }
        const response = await fetch(`${API_BASE}/strategy/apply`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          throw new Error(`Preview failed (${response.status})`);
        }
        const data = (await response.json()) as StrategyPreviewResponse;
        const preview: PreviewState = {
          id: data.preview_id,
          strategy: data.strategy as StrategyPreset,
          expiresAt: data.expires_at,
          delta: data.delta,
          explain: data.explain,
          weights: data.preview.weights,
        };
        schedulePreviewExpiry(preview.expiresAt);
        set({ preview, previewLoading: false, statusMessage: 'Preview ready', error: null });
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Preview failed';
        set({ previewLoading: false, error: message, statusMessage: null });
      }
    },

    confirmPreview: async () => {
      const { preview } = get();
      if (!preview) {
        set({ error: 'No preview to confirm' });
        return;
      }
      set({ confirmLoading: true, error: null });
      try {
        const response = await fetch(`${API_BASE}/strategy/assign`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ preview_id: preview.id }),
        });
        if (!response.ok) {
          throw new Error(`Confirm failed (${response.status})`);
        }
        const data = (await response.json()) as StrategyConfirmResponse;
        refreshWeightsFromResponse(data.applied.weights);
        clearPreviewTimeout();
        set({
          preview: null,
          confirmLoading: false,
          statusMessage: 'Strategy applied successfully',
        });
        if (data.undo_token && data.undo_expires_at) {
          startUndoCountdown(data.undo_token, data.undo_expires_at);
        } else {
          set({ undo: null });
        }
        void get().fetchChanges();
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Confirm failed';
        set({ confirmLoading: false, error: message });
      }
    },

    undoLast: async () => {
      const { undo } = get();
      if (!undo) {
        return;
      }
      set({ confirmLoading: true, error: null });
      try {
        const response = await fetch(`${API_BASE}/strategy/assign`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'undo', undo_id: undo.token }),
        });
        if (!response.ok) {
          throw new Error(`Undo failed (${response.status})`);
        }
        const data = (await response.json()) as StrategyUndoResponse;
        refreshWeightsFromResponse(data.restored.weights);
        clearUndoInterval();
        clearPreviewTimeout();
        set({
          undo: null,
          confirmLoading: false,
          statusMessage: 'Previous allocation restored',
        });
        void get().fetchChanges();
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Undo failed';
        set({ confirmLoading: false, error: message });
      }
    },

    dismissPreview: () => {
      clearPreviewTimeout();
      set({ preview: null });
    },
  };
});
