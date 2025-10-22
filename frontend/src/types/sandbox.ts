export interface SandboxRunRequest {
  strategy: string;
  days: number;
  initial_capital: number;
}

export interface SandboxRunResponse {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
}

export interface SandboxMetrics {
  total_return_pct: number;
  win_rate: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  average_slippage_bps: number;
  average_latency_ms: number;
}

export interface SandboxResult {
  metrics: SandboxMetrics;
  equity_curve: { day: number; equity: number }[];
  trades: { day: number; price: number; pnl_pct: number }[];
  completed_at: number;
}

export interface SandboxJobResponse {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  submitted_at: number;
  updated_at: number;
  request: SandboxRunRequest;
  result?: SandboxResult;
  error?: string;
}
