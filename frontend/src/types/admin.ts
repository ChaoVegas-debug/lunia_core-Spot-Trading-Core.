export interface AdminOverviewResponse {
  timestamp: string;
  actor: string;
  state: {
    auto_mode?: boolean;
    global_stop?: boolean;
    spot?: Record<string, unknown>;
    ops?: Record<string, unknown>;
  };
  funds: {
    limits: Record<string, unknown>;
    pending?: Record<string, unknown> | null;
  };
  recent_strategy_changes: Array<Record<string, unknown>>;
}

export interface AdminUsersResponse {
  count: number;
  items: Array<{
    user_id: string;
    last_action?: string | null;
    last_seen?: string | null;
    sources: string[];
  }>;
}

export interface AdminStrategyPerformanceResponse {
  count: number;
  items: Array<{
    strategy: string;
    trades: number;
    total_pnl: number;
    last_trade?: string | null;
  }>;
}
