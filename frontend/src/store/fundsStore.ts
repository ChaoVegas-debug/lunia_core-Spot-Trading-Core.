import { create } from 'zustand';
import {
  AggregatedBalancesResponse,
  ConfirmResponse,
  FundsLimitsPayload,
  FundsLimitsResponse,
  PreviewDelta,
  PreviewResponse,
  UndoResponse,
} from '../types';

interface CheckboxState {
  dontTouchStaking: boolean;
  dontCancelLimitOrders: boolean;
  autoConvertDust: boolean;
}

interface WorkingState {
  global: number;
  exchanges: Record<string, number>;
}

interface PreviewState {
  data: FundsLimitsPayload;
  delta?: PreviewDelta;
  expiresAt?: string;
}

interface UndoState {
  expiresAt: string;
  secondsLeft: number;
}

interface FundsState {
  loading: boolean;
  error: string | null;
  limits: FundsLimitsPayload | null;
  working: WorkingState;
  preview: PreviewState | null;
  isPreviewVisible: boolean;
  balances: AggregatedBalancesResponse | null;
  balancesLoading: boolean;
  undo: UndoState | null;
  checkboxes: CheckboxState;
  fetchLimits: () => Promise<void>;
  fetchBalances: () => Promise<void>;
  setGlobal: (value: number) => void;
  setExchange: (exchange: string, value: number) => void;
  setCheckbox: (key: keyof CheckboxState, value: boolean) => void;
  confirm: () => Promise<void>;
  undoChange: () => Promise<void>;
  dismissPreview: () => void;
  teardown: () => void;
}

const DEFAULT_CHECKBOXES: CheckboxState = {
  dontTouchStaking: false,
  dontCancelLimitOrders: false,
  autoConvertDust: false,
};

const clampPercent = (value: number): number => {
  if (Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
};

const toWorkingState = (limits: FundsLimitsPayload | null): WorkingState => {
  const global = limits?.global?.max_allocation_pct ?? 100;
  const exchanges: Record<string, number> = {};
  const source = limits?.exchanges ?? {};
  for (const [name, entry] of Object.entries(source)) {
    const pct = entry?.max_pct ?? 0;
    exchanges[name] = clampPercent(pct ?? 0);
  }
  return { global: clampPercent(global), exchanges };
};

const parseCheckboxNotes = (notes?: string | null): CheckboxState => {
  if (!notes) {
    return { ...DEFAULT_CHECKBOXES };
  }
  try {
    const parsed = JSON.parse(notes) as Partial<CheckboxState>;
    return { ...DEFAULT_CHECKBOXES, ...parsed };
  } catch (err) {
    return { ...DEFAULT_CHECKBOXES };
  }
};

const buildPreviewPayload = (state: FundsState) => {
  const exchangeLimits: Record<string, { max_pct: number; enabled: boolean }> = {};
  for (const [name, value] of Object.entries(state.working.exchanges)) {
    exchangeLimits[name] = { max_pct: clampPercent(value), enabled: true };
  }
  return {
    global_limit: {
      max_allocation_pct: clampPercent(state.working.global),
      notes: JSON.stringify(state.checkboxes),
    },
    exchange_limits: exchangeLimits,
  };
};

export const useFundsStore = create<FundsState>((set, get) => {
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

  const startUndoCountdown = (expiresAt: string) => {
    clearUndoInterval();
    const computeSeconds = () => {
      const target = new Date(expiresAt).getTime();
      const now = Date.now();
      return Math.max(0, Math.round((target - now) / 1000));
    };
    const tick = () => {
      const secondsLeft = computeSeconds();
      set((state) => ({
        undo: secondsLeft > 0 ? { expiresAt, secondsLeft } : null,
        error: state.error,
      }));
      if (secondsLeft <= 0) {
        clearUndoInterval();
      }
    };
    tick();
    undoInterval = setInterval(tick, 1000);
  };

  const applyPreview = async () => {
    const state = get();
    if (!state.limits) {
      return;
    }
    try {
      const response = await fetch('/api/v1/funds/limits/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPreviewPayload(state)),
      });
      if (!response.ok) {
        throw new Error(`Preview failed with status ${response.status}`);
      }
      const data = (await response.json()) as PreviewResponse;
      const working = toWorkingState(data.preview);
      set((prev) => ({
        preview: { data: data.preview, delta: data.preview_delta, expiresAt: data.expires_at },
        isPreviewVisible: true,
        working,
        error: null,
        limits: prev.limits,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Preview failed';
      set((prev) => ({
        error: message,
        isPreviewVisible: false,
        preview: null,
        working: prev.working,
      }));
    }
  };

  const schedulePreview = () => {
    clearPreviewTimeout();
    const state = get();
    if (!state.limits) {
      return;
    }
    previewTimeout = setTimeout(() => {
      applyPreview().catch((err) => {
        const message = err instanceof Error ? err.message : 'Preview failed';
        set((prev) => ({
          error: message,
          isPreviewVisible: false,
          preview: null,
          working: prev.working,
        }));
      });
    }, 250);
  };

  const syncWorkingFromLimits = (limits: FundsLimitsPayload | null) => {
    const working = toWorkingState(limits);
    set((state) => ({
      limits,
      working,
      checkboxes: limits ? parseCheckboxNotes(limits.global?.notes) : state.checkboxes,
      loading: false,
    }));
  };

  return {
    loading: false,
    error: null,
    limits: null,
    working: { global: 100, exchanges: {} },
    preview: null,
    isPreviewVisible: false,
    balances: null,
    balancesLoading: false,
    undo: null,
    checkboxes: { ...DEFAULT_CHECKBOXES },
    fetchLimits: async () => {
      set({ loading: true, error: null });
      try {
        const response = await fetch('/api/v1/funds/limits');
        if (!response.ok) {
          throw new Error(`Failed to load limits (${response.status})`);
        }
        const payload = (await response.json()) as FundsLimitsResponse;
        const limits = payload.limits;
        syncWorkingFromLimits(limits);
        if (payload.pending_preview) {
          set((state) => ({
            preview: {
              data: payload.pending_preview!.limits,
              delta: payload.pending_preview!.delta,
              expiresAt: payload.pending_preview!.expires_at,
            },
            isPreviewVisible: true,
            working: toWorkingState(payload.pending_preview!.limits),
            checkboxes: parseCheckboxNotes(payload.pending_preview!.limits.global?.notes),
            error: state.error,
          }));
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to load limits';
        set({ error: message, loading: false });
      }
    },
    fetchBalances: async () => {
      set({ balancesLoading: true });
      try {
        const response = await fetch('/api/v1/funds/balances/check');
        if (!response.ok) {
          throw new Error(`Failed to fetch balances (${response.status})`);
        }
        const payload = (await response.json()) as AggregatedBalancesResponse;
        set({ balances: payload, balancesLoading: false });
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to fetch balances';
        set({ error: message, balancesLoading: false });
      }
    },
    setGlobal: (value: number) => {
      set((state) => ({
        working: { ...state.working, global: clampPercent(value) },
        error: state.error,
      }));
      schedulePreview();
    },
    setExchange: (exchange: string, value: number) => {
      const key = exchange.toUpperCase();
      set((state) => ({
        working: {
          ...state.working,
          exchanges: { ...state.working.exchanges, [key]: clampPercent(value) },
        },
        error: state.error,
      }));
      schedulePreview();
    },
    setCheckbox: (key: keyof CheckboxState, value: boolean) => {
      set((state) => ({ checkboxes: { ...state.checkboxes, [key]: value } }));
      schedulePreview();
    },
    confirm: async () => {
      clearPreviewTimeout();
      try {
        const response = await fetch('/api/v1/funds/limits/confirm', { method: 'POST' });
        if (!response.ok) {
          throw new Error(`Confirm failed with status ${response.status}`);
        }
        const payload = (await response.json()) as ConfirmResponse;
        syncWorkingFromLimits(payload.applied);
        set({ preview: null, isPreviewVisible: false, error: null });
        if (payload.undo_expires_at) {
          startUndoCountdown(payload.undo_expires_at);
        } else {
          set({ undo: null });
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to confirm changes';
        set({ error: message });
      }
    },
    undoChange: async () => {
      clearPreviewTimeout();
      try {
        const response = await fetch('/api/v1/funds/limits/undo', { method: 'POST' });
        if (!response.ok) {
          throw new Error(`Undo failed with status ${response.status}`);
        }
        const payload = (await response.json()) as UndoResponse;
        clearUndoInterval();
        syncWorkingFromLimits(payload.restored);
        set({ preview: null, isPreviewVisible: false, undo: null, error: null });
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to undo changes';
        set({ error: message });
      }
    },
    dismissPreview: () => {
      clearPreviewTimeout();
      const limits = get().limits;
      set({
        preview: null,
        isPreviewVisible: false,
        working: toWorkingState(limits),
      });
    },
    teardown: () => {
      clearPreviewTimeout();
      clearUndoInterval();
    },
  };
});
