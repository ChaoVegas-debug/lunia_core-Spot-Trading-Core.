import * as React from 'react';
import { WidgetFrame, Button } from '@ui/components/foundation';
import { useHttpClient } from '@api-clients/http-client';
import { useRealtimeData } from '@utils/useRealtimeData';
import { useOptimisticMutation } from '@utils/optimistic';
import { engineStatusAdapter } from '@api-clients/adapters/engine-adapter';

export function MainControlBoard() {
  const http = useHttpClient();
  const { data: engines, connected: enginesConnected } = useRealtimeData(
    'engine.status',
    engineStatusAdapter,
  );
  const { data: mode, connected: modeConnected } = useRealtimeData(
    'core.mode.changed',
    (payload: any) => payload?.mode,
  );

  const { mutate: switchMode, isLoading: modeLoading } = useOptimisticMutation(
    (newMode: 'auto' | 'semi' | 'manual' | 'stop') =>
      http.post('/core/mode', { mode: newMode }),
    (_, newMode) => newMode,
  );

  const { mutate: toggleEngine, isLoading: engineLoading } = useOptimisticMutation(
    ({
      name,
      on,
    }: {
      name: 'spot' | 'futures' | 'arbitrage' | 'options' | 'hft';
      on: boolean;
    }) => http.post(`/core/engine/${name}/${on ? 'on' : 'off'}`),
    (previous: any, { name, on }) => ({
      ...(previous ?? {}),
      [name]: on ? 'on' : 'off',
    }),
  );

  return (
    <WidgetFrame
      title="Control Board"
      wsChannels={['engine.status', 'core.mode.changed', 'core.system.stopped', 'core.system.halted']}
    >
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        {(['auto', 'semi', 'manual', 'stop'] as const).map((currentMode) => (
          <Button
            key={currentMode}
            variant={mode === currentMode ? 'primary' : 'secondary'}
            onClick={() => switchMode(currentMode)}
            isLoading={modeLoading}
            disabled={!modeConnected}
            className="h-12 capitalize text-sm"
          >
            {currentMode === 'auto'
              ? '🟢'
              : currentMode === 'semi'
              ? '🟡'
              : currentMode === 'manual'
              ? '🔴'
              : '⏹️'}{' '}
            {currentMode}
          </Button>
        ))}
        <Button
          variant="danger"
          onClick={() => http.post('/core/stop')}
          className="h-12 text-sm"
        >
          🚨 E-Stop
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {(['spot', 'futures', 'arbitrage', 'options', 'hft'] as const).map((name) => (
          <div key={name} className="text-center">
            <div className="text-sm text-gray-400 mb-2 capitalize">{name}</div>
            <label className="inline-flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4"
                disabled={engineLoading || !enginesConnected}
                checked={(engines?.[name] ?? 'off') === 'on'}
                onChange={(event) =>
                  toggleEngine({ name, on: event.target.checked })
                }
              />
              <span
                className={`${(engines?.[name] ?? 'off') === 'on' ? 'text-green-400' : 'text-red-400'} ${
                  !enginesConnected ? 'opacity-50' : ''
                }`}
              >
                {enginesConnected
                  ? (engines?.[name] ?? 'off') === 'on'
                    ? 'ACTIVE'
                    : 'INACTIVE'
                  : 'OFFLINE'}
              </span>
            </label>
          </div>
        ))}
      </div>

      <div className="flex justify-between items-center mt-4 text-xs text-gray-400">
        <span>Mode: {modeConnected ? '● Live' : '○ Offline'}</span>
        <span>Engines: {enginesConnected ? '● Live' : '○ Offline'}</span>
      </div>
    </WidgetFrame>
  );
}
