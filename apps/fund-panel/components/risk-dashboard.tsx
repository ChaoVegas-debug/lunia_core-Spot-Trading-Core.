import * as React from 'react';
import { WidgetFrame } from '@ui/components/foundation';
import { AccessibleSlider } from '@ui/components/accessible-slider';
import { useHttpClient } from '@api-clients/http-client';
import { useRealtimeData } from '@utils/useRealtimeData';
import { useOptimisticMutation } from '@utils/optimistic';
import { riskLimitsAdapter } from '@api-clients/adapters/risk-adapter';

export function RiskDashboard() {
  const http = useHttpClient();
  const { data: limits } = useRealtimeData('risk.limit.changed', riskLimitsAdapter, '/risk/get');
  const { mutate: setLimit, isLoading } = useOptimisticMutation(
    ({ key, value }: { key: 'drawdown' | 'daily' | 'leverage'; value: number }) =>
      http.post(`/risk/set-${key}`, { [key]: value }),
    (prev: any, { key, value }) => ({
      ...(prev ?? {}),
      [key]: value,
    }),
  );

  return (
    <WidgetFrame title="Risk Management" wsChannels={['risk.limit.changed', 'risk.alert']}>
      <div className="space-y-4">
        <AccessibleSlider
          label="Max Drawdown"
          value={limits?.drawdown ?? 10}
          min={1}
          max={20}
          step={0.5}
          disabled={isLoading}
          onChange={(value) => setLimit({ key: 'drawdown', value })}
        />
        <AccessibleSlider
          label="Daily Loss Limit"
          value={limits?.daily ?? 2}
          min={0.5}
          max={5}
          step={0.1}
          disabled={isLoading}
          onChange={(value) => setLimit({ key: 'daily', value })}
        />
        <AccessibleSlider
          label="Leverage (x)"
          value={limits?.leverage ?? 2}
          min={1}
          max={10}
          step={0.1}
          disabled={isLoading}
          onChange={(value) => setLimit({ key: 'leverage', value })}
        />
      </div>
    </WidgetFrame>
  );
}
