import { create } from 'zustand';
import { FeatureFlags } from '../types/featureFlags';

const defaultFlags: FeatureFlags = {
  manualMode: true,
  explainCardsV2: true,
  fundsLimits: true,
  sandbox: true,
  scheduler: true,
};

function readEnvFlag(name: string, fallback: boolean) {
  const value = window?.__LUNIA_FLAGS__?.[name] ?? import.meta.env[`VITE_${name}`];
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    return ['1', 'true', 'on', 'yes'].includes(value.toLowerCase());
  }
  return fallback;
}

export const useFeatureFlags = create(() => ({
  manualMode: readEnvFlag('FEATURE_MANUAL_MODE', defaultFlags.manualMode),
  explainCardsV2: readEnvFlag('FEATURE_EXPLAIN_CARDS_V2', defaultFlags.explainCardsV2),
  fundsLimits: readEnvFlag('FEATURE_FUNDS_LIMITS', defaultFlags.fundsLimits),
  isSandboxEnabled: readEnvFlag('FEATURE_SANDBOX', defaultFlags.sandbox),
  scheduler: readEnvFlag('FEATURE_SCHEDULER', defaultFlags.scheduler),
}));

export type FeatureFlagStore = ReturnType<typeof useFeatureFlags.getState>;
