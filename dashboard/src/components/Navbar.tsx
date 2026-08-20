import React from 'react';
import { ShieldCheck, User, Database } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="h-16 border-b border-[#E2E8F0] bg-white px-6 flex items-center justify-between sticky top-0 z-40 shadow-xs">
      {/* University Brand & Portal Title */}
      <div className="flex items-center gap-3.5">
        <div className="w-9 h-9 rounded-lg bg-[#800000] text-white flex items-center justify-center font-black text-sm shadow-xs tracking-tight">
          FU
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm text-[#0F172A] tracking-tight">
              OvaLens
            </span>
            <span className="text-slate-300 text-xs">|</span>
            <span className="text-xs font-semibold text-slate-600">
              Foundation University Hatchery Portal
            </span>
          </div>
          <p className="text-[11px] text-slate-500 hidden sm:block">
            Automated Duck Egg Candling & Incubation Management
          </p>
        </div>
      </div>

      {/* Right Controls: Database Sync Status & User Profile */}
      <div className="flex items-center gap-4">
        {/* Offline-First Edge Sync Pill */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-50 border border-slate-200 text-xs">
          <Database className="w-3.5 h-3.5 text-emerald-700" />
          <span className="font-medium text-slate-700">Edge SQLite WAL:</span>
          <span className="font-semibold text-emerald-700">Synced</span>
        </div>

        {/* User Operator Profile */}
        <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-maroon-50 text-[#800000] border border-maroon-200 flex items-center justify-center text-xs font-bold">
            RG
          </div>
          <div className="hidden md:block text-left">
            <p className="text-xs font-bold text-[#0F172A] leading-tight">Ryle Gabotero</p>
            <p className="text-[11px] text-slate-500">Lead Hatchery Operator</p>
          </div>
        </div>
      </div>
    </header>
  );
};
