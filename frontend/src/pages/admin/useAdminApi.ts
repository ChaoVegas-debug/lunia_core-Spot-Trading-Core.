import { useEffect, useState } from 'react';

import { adminHeaders, useAdminStore } from '../../store/adminStore';

interface AdminApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  token: string;
  refetch: () => Promise<void>;
}

export function useAdminApi<T>(endpoint: string, deps: unknown[] = []): AdminApiState<T> {
  const token = useAdminStore((state) => state.token);
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  async function load(signal?: AbortSignal) {
    if (!token) {
      setData(null);
      setError('Admin token required');
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(endpoint, {
        headers: adminHeaders(token),
        signal,
      });
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const payload = (await response.json()) as T;
      setData(payload);
    } catch (err) {
      if (signal?.aborted) return;
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      setData(null);
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint, token, ...deps]);

  return {
    data,
    loading,
    error,
    token,
    refetch: () => load(),
  };
}
