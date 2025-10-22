import { useMemo, useState } from 'react';

import { GlassCard } from '../../components/UI/GlassCard';
import type { AdminUsersResponse } from '../../types';
import { useAdminApi } from './useAdminApi';

export function AdminUsers() {
  const [search, setSearch] = useState('');
  const { data, error, loading, token, refetch } = useAdminApi<AdminUsersResponse>(
    `/api/v1/admin/users${search ? `?search=${encodeURIComponent(search)}` : ''}`,
    [search],
  );

  const items = useMemo(() => data?.items ?? [], [data]);

  if (!token) {
    return <GlassCard title="Admin Token Required">Provide the admin token to inspect users.</GlassCard>;
  }

  return (
    <GlassCard title="User Directory" subtitle="Actors interacting with strategy & funds modules">
      <div className="form-row">
        <input
          type="search"
          placeholder="Search actors…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <button type="button" onClick={() => refetch()}>
          Refresh
        </button>
      </div>
      {loading && <p>Loading…</p>}
      {error && <p className="error-text">{error}</p>}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Last action</th>
              <th>Last seen</th>
              <th>Sources</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={4}>No matching actors.</td>
              </tr>
            )}
            {items.map((item) => (
              <tr key={item.user_id}>
                <td>{item.user_id}</td>
                <td>{item.last_action ?? '—'}</td>
                <td>{item.last_seen ?? '—'}</td>
                <td>{item.sources.join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </GlassCard>
  );
}
