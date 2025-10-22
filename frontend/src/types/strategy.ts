export type StrategyPreset = 'conservative' | 'balanced' | 'aggressive' | 'custom';

export interface StrategyPreviewDeltaEntry {
  before: number;
  after: number;
  delta: number;
  direction: 'increase' | 'decrease';
}

export interface StrategyPreviewExplain {
  summary?: string;
  rationale?: string | null;
  confidence?: number;
  changes?: Array<{
    strategy: string;
    before: number;
    after: number;
    delta: number;
    direction: 'increase' | 'decrease';
  }>;
  generated_at?: string;
  [key: string]: unknown;
}

export interface StrategyPreviewResponse {
  preview_id: string;
  strategy: string;
  expires_at: string;
  preview: {
    weights: Record<string, number>;
  };
  delta: Record<string, StrategyPreviewDeltaEntry>;
  explain?: StrategyPreviewExplain;
}

export interface StrategyConfirmResponse {
  status: 'applied';
  applied: {
    weights: Record<string, number>;
  };
  undo_token?: string;
  undo_expires_at?: string;
  explain?: StrategyPreviewExplain;
  change?: Record<string, unknown>;
}

export interface StrategyUndoResponse {
  status: 'restored';
  restored: {
    weights: Record<string, number>;
  };
  change?: Record<string, unknown>;
}

export interface StrategyChangeEntry {
  ts: string;
  action: string;
  actor: string;
  payload: Record<string, unknown>;
  hash?: string;
  prev_hash?: string | null;
}

export interface StrategyWeightsState {
  enabled: boolean;
  weights: Record<string, number>;
}
