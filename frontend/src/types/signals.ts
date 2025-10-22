export interface ExplanationLayer {
  title?: string;
  summary: string;
  bullets?: string[];
  details?: Record<string, unknown>;
}

export interface ExplanationLayers {
  beginner?: ExplanationLayer;
  trader?: ExplanationLayer;
  pro?: ExplanationLayer;
  [key: string]: ExplanationLayer | undefined;
}

export interface AlternativeScenario {
  label: string;
  probability: number;
  action: string;
  summary?: string;
}

export interface RiskMetrics {
  [key: string]: string | number | undefined;
  notional_usd?: number;
  position_size?: number;
  stop_loss_pct?: number;
  take_profit_pct?: number;
  value_at_risk_usd?: number;
  risk_reward_ratio?: number;
  exposure_pct?: number;
  leverage?: number;
  regime_volatility?: number;
}

export interface SignalItem {
  symbol: string;
  side: string;
  strategy?: string;
  score?: number;
  price?: number;
  qty?: number;
  notional_usd?: number;
  stop_pct?: number;
  take_pct?: number;
  generated_at?: string;
  certainty_score?: number;
  explanation_layers?: ExplanationLayers;
  alternative_scenarios?: AlternativeScenario[];
  risk_metrics?: RiskMetrics;
}

