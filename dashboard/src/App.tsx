import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { LoginPage } from './pages/LoginPage';
import { OverviewPage } from './pages/OverviewPage';
import { BatchesPage } from './pages/BatchesPage';
import { ScanExplorerPage } from './pages/ScanExplorerPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { DevicesPage } from './pages/DevicesPage';
import { RecordsPage } from './pages/RecordsPage';
import { ModelsPage } from './pages/ModelsPage';
import { UsersPage } from './pages/UsersPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { SettingsPage } from './pages/SettingsPage';

const ProtectedLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = React.useState(false);
  const mainRef = React.useRef<HTMLElement>(null);

  // Smooth scroll to top when changing views
  React.useEffect(() => {
    if (mainRef.current) {
      mainRef.current.scrollTo({ top: 0, behavior: 'instant' });
    }
  }, [location.pathname]);

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[#F8FAFC]">
        <div className="text-center space-y-2 animate-scale-in">
          <div className="w-8 h-8 border-3 border-[#800000] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-semibold text-slate-600">Initializing OvaLens Hatchery...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <div className="h-screen w-screen overflow-hidden bg-[#F8FAFC] text-[#0F172A] flex flex-col font-sans">
      <Navbar onToggleSidebar={() => setIsMobileSidebarOpen(prev => !prev)} />
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar isOpen={isMobileSidebarOpen} onClose={() => setIsMobileSidebarOpen(false)} />
        <main ref={mainRef} className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 w-full custom-scrollbar">
          <div key={location.pathname} className="max-w-7xl mx-auto animate-page-enter">
            <Routes location={location}>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/batches" element={<BatchesPage />} />
              <Route path="/scans" element={<ScanExplorerPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/devices" element={<DevicesPage />} />
              <Route path="/records" element={<RecordsPage />} />
              <Route path="/models" element={<ModelsPage />} />
              <Route path="/users" element={<UsersPage />} />
              <Route path="/logs" element={<AuditLogsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
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
