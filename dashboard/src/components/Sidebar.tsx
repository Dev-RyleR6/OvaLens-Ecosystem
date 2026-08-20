import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Layers,
  ScanLine,
  TrendingUp,
  Cpu,
  CheckCircle2,
  HardDrive,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export const Sidebar: React.FC = () => {
  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/batches', label: 'Incubation Batches', icon: Layers },
    { to: '/scans', label: 'Candling Scans', icon: ScanLine },
    { to: '/analytics', label: 'Economics & Salvage', icon: TrendingUp },
    { to: '/devices', label: 'Edge Sorter Nodes', icon: Cpu },
  ];

  return (
    <aside className="w-64 border-r border-[#E2E8F0] bg-white flex flex-col justify-between flex-shrink-0 z-30 min-h-[calc(100vh-4rem)]">
      {/* Navigation List */}
      <div className="p-4 space-y-1.5">
        <p className="px-3 pb-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
          Management
        </p>

        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-[#800000] text-white shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                )
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      {/* Bottom Hardware Status Card */}
      <div className="p-4 m-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-slate-700" />
            <span className="text-xs font-bold text-slate-800">Station-01-RP5</span>
          </div>
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
            Online
          </span>
        </div>

        <p className="text-[11px] text-slate-500 leading-snug">
          ONNX FP16 Vision Engine active on conveyor lane 1.
        </p>
      </div>
    </aside>
  );
};
