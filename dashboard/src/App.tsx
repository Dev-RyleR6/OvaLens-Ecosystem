import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { OverviewPage } from './pages/OverviewPage';
import { BatchesPage } from './pages/BatchesPage';
import { ScanExplorerPage } from './pages/ScanExplorerPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { DevicesPage } from './pages/DevicesPage';

export const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#0F172A] text-slate-100 flex flex-col">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6 md:p-8 max-w-7xl mx-auto w-full">
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
export default App;
