import React from 'react';
import { Database, ShieldCheck } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="h-16 border-b border-slate-200/80 glass-surface px-6 flex items-center justify-between sticky top-0 z-40 shadow-xs">
      {/* University Brand & Portal Title */}
      <div className="flex items-center gap-3.5 group cursor-default">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#800000] to-[#5C0000] text-white flex items-center justify-center font-black text-sm shadow-xs tracking-tight transition-transform duration-200 group-hover:scale-105">
          FU
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-extrabold text-sm text-[#0F172A] tracking-tight">
              OvaLens
            </span>
            <span className="text-slate-300 text-xs">|</span>
            <span className="text-xs font-semibold text-slate-700">
              Foundation University Hatchery Portal
            </span>
          </div>
          <p className="text-[11px] text-slate-500 hidden sm:block">
            Automated Duck Egg Candling & Incubation Management
          </p>
        </div>
      </div>

      {/* Right Controls: Database Sync Status & User Profile */}
      <div className="flex items-center gap-3.5">
        {/* Offline-First Edge Sync Pill */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50/70 border border-emerald-200/80 text-xs transition-colors hover:bg-emerald-50">
          <div className="relative flex items-center justify-center">
            <span className="w-2 h-2 rounded-full bg-emerald-600 animate-ping absolute opacity-75" />
            <span className="w-2 h-2 rounded-full bg-emerald-600 relative" />
          </div>
          <span className="font-medium text-slate-700">Edge SQLite WAL:</span>
          <span className="font-bold text-emerald-800">Synced</span>
        </div>

        {/* User Operator Profile */}
        <div className="flex items-center gap-2.5 pl-3 border-l border-slate-200/80 group cursor-pointer">
          <div className="w-8 h-8 rounded-full bg-maroon-50 text-[#800000] border border-maroon-200/90 flex items-center justify-center text-xs font-extrabold transition-transform duration-200 group-hover:scale-105 group-hover:bg-[#800000] group-hover:text-white">
            RG
          </div>
          <div className="hidden md:block text-left">
            <p className="text-xs font-bold text-[#0F172A] leading-tight group-hover:text-[#800000] transition-colors">
              Ryle Gabotero
            </p>
            <p className="text-[10px] text-slate-500 font-medium">Lead Hatchery Operator</p>
          </div>
        </div>
      </div>
    </header>
  );
};
