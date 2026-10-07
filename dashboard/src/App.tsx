import { usePreferences } from './hooks/usePreferences';
import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { LoginPage } from './pages/LoginPage';
const OverviewPage = React.lazy(() => import('./pages/OverviewPage').then(module => ({ default: module.OverviewPage })));
const BatchesPage = React.lazy(() => import('./pages/BatchesPage').then(module => ({ default: module.BatchesPage })));
const ScanExplorerPage = React.lazy(() => import('./pages/ScanExplorerPage').then(module => ({ default: module.ScanExplorerPage })));
const AnalyticsPage = React.lazy(() => import('./pages/AnalyticsPage').then(module => ({ default: module.AnalyticsPage })));
const DevicesPage = React.lazy(() => import('./pages/DevicesPage').then(module => ({ default: module.DevicesPage })));
const UsersPage = React.lazy(() => import('./pages/UsersPage').then(module => ({ default: module.UsersPage })));
const SettingsPage = React.lazy(() => import('./pages/SettingsPage').then(module => ({ default: module.SettingsPage })));
import { RoleProtectedRoute } from './components/RoleProtectedRoute';

const ProtectedLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = React.useState(false);
  const mainRef = React.useRef<HTMLElement>(null);
  React.useEffect(() => {
    mainRef.current?.scrollTo({ top: 0, behavior: 'instant' });
  }, [location.pathname]);

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-2 ">
          <div className="w-8 h-8 border-3 border-[#800000] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-semibold text-slate-600">Initializing OvaLens Hatchery...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="h-[100dvh] w-full overflow-hidden bg-background text-foreground flex flex-col font-sans relative">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <Navbar sidebarOpen={isMobileSidebarOpen} onToggleSidebar={() => setIsMobileSidebarOpen(prev => !prev)} />
      <div className="flex flex-1 min-h-0 overflow-hidden relative">
        <Sidebar isOpen={isMobileSidebarOpen} onClose={() => setIsMobileSidebarOpen(false)} />
        <main ref={mainRef} id="main-content" tabIndex={-1} className="dashboard-content min-w-0 flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 w-full custom-scrollbar">
          <div key={location.pathname} className="max-w-7xl mx-auto min-w-0 ">
            <React.Suspense fallback={<p role="status" className="py-8 text-slate-600">Loading page…</p>}>
            <Routes location={location}>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/batches" element={<BatchesPage />} />
              <Route path="/scans" element={<ScanExplorerPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/devices" element={<DevicesPage />} />
              
              {/* RBAC Protected Administration Routes */}
              <Route
                path="/users"
                element={
                  <RoleProtectedRoute allowedRoles={['ADMIN']} moduleName="User & Access Control">
                    <UsersPage />
                  </RoleProtectedRoute>
                }
              />
              <Route
                path="/settings"
                element={
                  <RoleProtectedRoute allowedRoles={['ADMIN', 'MANAGER', 'OPERATOR']} moduleName="Settings">
                    <SettingsPage />
                  </RoleProtectedRoute>
                }
              />
              <Route path="*" element={<div className="space-y-4"><h1>Page not found</h1><a href="/" className="primary-action">Return to overview</a></div>} />
            </Routes>
            </React.Suspense>
          </div>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  const { theme, tableDensity } = usePreferences();
  React.useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.density = tableDensity;
    document.documentElement.style.colorScheme = theme;
  }, [theme, tableDensity]);
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/*" element={<ProtectedLayout />} />
      </Routes>
    </AuthProvider>
  );
};

export default App;
