import * as React from 'react';
import { WidgetFrame, Button } from '@ui/components/foundation';
import { useHttpClient } from '@api-clients/http-client';
import { useDebouncedPreview } from '@utils/useDebouncedPreview';
import { useOptimisticMutation } from '@utils/optimistic';
import { generateIdempotencyKey } from '@utils/idempotency';

export function UtilizationSlider({
  scope,
  venue,
  core,
  strategy,
}: {
  scope: 'global' | 'venue' | 'core' | 'strategy';
  venue?: string;
  core?: string;
  strategy?: string;
}) {
  const http = useHttpClient();
  const [value, setValue] = React.useState(50);
  const [undoToken, setUndoToken] = React.useState<string>();

  const { preview, isLoading: previewLoading, error, triggerPreview } = useDebouncedPreview<
    number,
    any
  >(async (percent) => {
    const response = await http.post('/portfolio/utilization/preview', {
      scope,
      venue,
      core,
      strategy,
      percent,
      idempotency_key: generateIdempotencyKey(),
    });
    return response?.data ?? response;
  });

  const { mutate: commit, isLoading: committing } = useOptimisticMutation(
    async (percent: number) =>
      http.post('/portfolio/utilization/commit', {
        scope,
        venue,
        core,
        strategy,
        percent,
        confirmed: true,
        idempotency_key: generateIdempotencyKey(),
      }),
    (previous: any, percent) => ({ percent }),
  );

  const handleCommit = async () => {
    const result: any = await commit(value);
    if (result?.undo_token) {
      setUndoToken(result.undo_token);
    }
  };

  const handleUndo = async () => {
    if (!undoToken) return;
    await http.post('/portfolio/utilization/undo', { undo_token: undoToken });
    setUndoToken(undefined);
  };

  return (
    <WidgetFrame
      title={`Utilization (${scope})`}
      wsChannels={['portfolio.utilization.previewed', 'portfolio.utilization.changed', 'portfolio.utilization.reverted']}
      rightSlot={
        undoToken && (
          <Button size="sm" variant="secondary" onClick={handleUndo}>
            ↩ Undo
          </Button>
        )
      }
      errorMessage={error?.message}
    >
      <div className="flex items-center gap-4">
        <input
          type="range"
          min={0}
          max={100}
          value={value}
          disabled={committing}
          onChange={(event) => {
            const percent = Number(event.target.value);
            setValue(percent);
            triggerPreview(percent);
          }}
          className="flex-1"
        />
        <input
          type="number"
          min={0}
          max={100}
          value={value}
          disabled={committing}
          onChange={(event) => {
            const percent = Number(event.target.value);
            setValue(percent);
            triggerPreview(percent);
          }}
          className="w-20 bg-gray-700 border border-gray-600 rounded text-white px-2 py-1 text-center"
        />
        <Button onClick={handleCommit} isLoading={committing} disabled={previewLoading || committing}>
          Apply
        </Button>
      </div>

      {previewLoading && <div className="text-sm text-gray-400 mt-2">Calculating preview…</div>}
      {preview && !previewLoading && (
        <div className="text-sm text-gray-300 mt-3 space-y-1">
          <div>Notional: ${preview.notional_usd?.toLocaleString?.() ?? preview.notional_usd}</div>
          <div>Cap: {preview.caps?.hard_cap}%</div>
          {preview.risk_flags?.includes('exceeds_cap') && (
            <div className="text-red-400 font-semibold">⚠️ CAP EXCEEDED</div>
          )}
        </div>
      )}
    </WidgetFrame>
  );
}
