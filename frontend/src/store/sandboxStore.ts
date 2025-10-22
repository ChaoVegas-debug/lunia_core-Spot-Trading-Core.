import { create } from 'zustand';

import { SandboxJobResponse, SandboxRunRequest, SandboxRunResponse } from '../types';

interface SandboxState {
  job: SandboxJobResponse | null;
  submitting: boolean;
  error: string | null;
  run: (payload: SandboxRunRequest) => Promise<void>;
  reset: () => void;
}

const POLL_INTERVAL_MS = 1000;

export const useSandboxStore = create<SandboxState>((set) => {
  let pollTimer: ReturnType<typeof setInterval> | null = null;

  const clearTimer = () => {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  };

  const fetchJob = async (jobId: string) => {
    try {
      const response = await fetch(`/api/v1/sandbox/${jobId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch job ${jobId}`);
      }
      const payload = (await response.json()) as SandboxJobResponse;
      set({ job: payload, submitting: false, error: null });
      if (payload.status === 'completed' || payload.status === 'failed') {
        clearTimer();
      }
    } catch (error) {
      clearTimer();
      set({ error: error instanceof Error ? error.message : 'Unable to fetch job', submitting: false });
    }
  };

  return {
    job: null,
    submitting: false,
    error: null,
    run: async (payload: SandboxRunRequest) => {
      clearTimer();
      set({ submitting: true, error: null });
      try {
        const response = await fetch('/api/v1/sandbox/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          throw new Error(`Run failed with status ${response.status}`);
        }
        const data = (await response.json()) as SandboxRunResponse;
        const job: SandboxJobResponse = {
          job_id: data.job_id,
          status: data.status,
          submitted_at: Date.now() / 1000,
          updated_at: Date.now() / 1000,
          request: payload,
        };
        set({ job, submitting: data.status !== 'completed', error: null });
        if (data.status !== 'completed') {
          pollTimer = setInterval(() => {
            fetchJob(data.job_id).catch(() => {
              /* errors handled in fetchJob */
            });
          }, POLL_INTERVAL_MS);
        } else {
          await fetchJob(data.job_id);
        }
      } catch (error) {
        clearTimer();
        set({ error: error instanceof Error ? error.message : 'Unable to run backtest', submitting: false });
      }
    },
    reset: () => {
      clearTimer();
      set({ job: null, error: null, submitting: false });
    },
  };
});
