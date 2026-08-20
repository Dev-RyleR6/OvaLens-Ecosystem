import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { OverviewPage } from './pages/OverviewPage';
import { BatchesPage } from './pages/BatchesPage';
import { ScanExplorerPage } from './pages/ScanExplorerPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { DevicesPage } from './pages/DevicesPage';

export const AppContent: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Navbar sidebarOpen={!isCollapsed} setSidebarOpen={() => setIsCollapsed(prev => !prev)} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 max-w-7xl mx-auto w-full">
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/batches" element={<BatchesPage />} />
            <Route path="/scans" element={<ScanExplorerPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/devices" element={<DevicesPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
};

export default App;
