export interface GlobalLimit {
  max_allocation_pct: number;
  notes?: string | null;
}

export interface ExchangeLimit {
  exchange: string;
  max_usd?: number | null;
  max_pct?: number | null;
  enabled: boolean;
}

export interface PortfolioLimit {
  symbol: string;
  max_usd?: number | null;
  max_pct?: number | null;
  strategy?: string | null;
}

export interface FundsLimitsPayload {
  global: GlobalLimit;
  exchanges: Record<string, ExchangeLimit>;
  portfolio?: Record<string, PortfolioLimit>;
  updated_at?: string;
  updated_by?: string;
}

export interface PreviewDeltaEntry<T = unknown> {
  before?: T;
  after?: T;
}

export interface PreviewDelta {
  global_limit?: PreviewDeltaEntry<GlobalLimit>;
  exchange_limits?: Record<string, PreviewDeltaEntry<ExchangeLimit>>;
  portfolio_limits?: Record<string, PreviewDeltaEntry<PortfolioLimit>>;
}

export interface PreviewResponse {
  preview: FundsLimitsPayload;
  preview_delta?: PreviewDelta;
  expires_at?: string;
}

export interface ConfirmResponse {
  status: string;
  applied: FundsLimitsPayload;
  undo_expires_at?: string;
}

export interface UndoResponse {
  status: string;
  restored: FundsLimitsPayload;
}

export interface FundsLimitsResponse {
  limits: FundsLimitsPayload;
  pending_preview?: {
    limits: FundsLimitsPayload;
    delta?: PreviewDelta;
    expires_at?: string;
  };
}

export interface AggregatedBalancesResponse {
  timestamp: string;
  spot: Record<string, Record<string, string | number>>;
  futures?: Record<string, unknown> | null;
  aggregated: Record<string, { total: number }>;
  summary?: {
    balances: Array<{ asset: string; free: number; locked: number }>;
  };
}
