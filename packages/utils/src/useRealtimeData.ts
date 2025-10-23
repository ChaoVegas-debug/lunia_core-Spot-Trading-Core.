import * as React from 'react';
import { useWebSocket } from '@api-clients/ws-client';
import { useHttpClient } from '@api-clients/http-client';

export function useRealtimeData<T>(
  wsChannel: string,
  adapter: (payload: any) => T,
  endpoint?: string,
) {
  const [data, setData] = React.useState<T>();
  const [connected, setConnected] = React.useState(false);
  const [error, setError] = React.useState<Error>();
  const ws = useWebSocket();
  const http = useHttpClient();

  React.useEffect(() => {
    if (endpoint) {
      http
        .get(endpoint)
        .then((json: any) => setData(adapter(json?.data ?? json)))
        .catch((err: Error) => setError(err));
    }
  }, [endpoint, adapter, http]);

  React.useEffect(() => {
    const handler = (payload: any) => {
      try {
        setData(adapter(payload));
        setError(undefined);
      } catch (err) {
        setError(err as Error);
      }
    };

    ws.subscribe(wsChannel, handler);
    setConnected(true);

    return () => {
      ws.unsubscribe(wsChannel, handler);
      setConnected(false);
    };
  }, [wsChannel, adapter, ws]);

  return { data, connected, error, setData };
}
