import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { useFeatureFlags } from './store/featureFlags';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const FundsInWork = lazy(() => import('./pages/FundsInWork'));
const Strategies = lazy(() => import('./pages/Strategies'));
const Sandbox = lazy(() => import('./pages/Sandbox'));
const Admin = lazy(() => import('./pages/Admin'));
const BotControl = lazy(() => import('./pages/BotControl'));
const Portfolio = lazy(() => import('./pages/Portfolio'));
const Signals = lazy(() => import('./pages/Signals'));
const Settings = lazy(() => import('./pages/Settings'));

export default function App() {
  const flags = useFeatureFlags();

  return (
    <Layout>
      <Suspense fallback={<div className="page-loading">Loading…</div>}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/funds" element={<FundsInWork />} />
          <Route path="/strategies" element={<Strategies />} />
          {flags.isSandboxEnabled && <Route path="/sandbox" element={<Sandbox />} />}
          <Route path="/admin" element={<Admin />} />
          <Route path="/bot" element={<BotControl />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
