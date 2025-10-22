import { useState } from 'react';

import { GlassCard } from '../components/UI/GlassCard';
import { useAdminStore } from '../store/adminStore';
import { AdminInfra } from './admin/Infra';
import { AdminMarketing } from './admin/Marketing';
import { AdminOverview } from './admin/Overview';
import { AdminRisk } from './admin/Risk';
import { AdminStrategies } from './admin/Strategies';
import { AdminUsers } from './admin/Users';
import './pages.css';

const tabs = [
  { id: 'overview', label: 'Overview', element: <AdminOverview /> },
  { id: 'users', label: 'Users', element: <AdminUsers /> },
  { id: 'strategies', label: 'Strategies', element: <AdminStrategies /> },
  { id: 'risk', label: 'Risk', element: <AdminRisk /> },
  { id: 'infra', label: 'Infra', element: <AdminInfra /> },
  { id: 'marketing', label: 'Marketing', element: <AdminMarketing /> },
];

export default function Admin() {
  const { token, setToken } = useAdminStore();
  const [active, setActive] = useState('overview');

  const activeTab = tabs.find((tab) => tab.id === active) ?? tabs[0];

  return (
    <div className="admin-page">
      <GlassCard title="Admin Access" subtitle="Provide token for privileged endpoints">
        <div className="form-row">
          <input
            type="password"
            placeholder="Admin token"
            value={token}
            onChange={(event) => setToken(event.target.value)}
          />
          <span className="hint-text">
            Token stored locally for this browser session. Clear the field to remove.
          </span>
        </div>
      </GlassCard>
      <div className="admin-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={tab.id === active ? 'active' : ''}
            onClick={() => setActive(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="admin-content">{activeTab.element}</div>
    </div>
  );
}
