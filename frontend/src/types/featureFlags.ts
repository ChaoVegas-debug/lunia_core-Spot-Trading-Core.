export interface FeatureFlags {
  manualMode: boolean;
  explainCardsV2: boolean;
  fundsLimits: boolean;
  sandbox: boolean;
  scheduler: boolean;
}

declare global {
  interface Window {
    __LUNIA_FLAGS__?: Record<string, unknown>;
  }
}
