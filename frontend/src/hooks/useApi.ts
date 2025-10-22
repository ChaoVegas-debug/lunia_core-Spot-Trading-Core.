import { useEffect, useState } from 'react';

type HttpMethod = 'GET' | 'POST';

interface ApiOptions<TBody> {
  method?: HttpMethod;
  body?: TBody;
  skip?: boolean;
}

export function useApi<TResponse = unknown, TBody = unknown>(endpoint: string, options: ApiOptions<TBody> = {}) {
  const { method = 'GET', body, skip = false } = options;
  const [data, setData] = useState<TResponse | null>(null);
  const [loading, setLoading] = useState(!skip);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (skip) return;
    let ignore = false;

    async function fetchData() {
      try {
        setLoading(true);
        const response = await fetch(endpoint, {
          method,
          headers: body ? { 'Content-Type': 'application/json' } : undefined,
          body: body ? JSON.stringify(body) : undefined,
        });
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const payload = (await response.json()) as TResponse;
        if (!ignore) {
          setData(payload);
        }
      } catch (err) {
        if (!ignore) {
          setError(err instanceof Error ? err : new Error('Unknown error'));
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    fetchData();
    return () => {
      ignore = true;
    };
  }, [endpoint, method, body, skip]);

  return { data, loading, error };
}
