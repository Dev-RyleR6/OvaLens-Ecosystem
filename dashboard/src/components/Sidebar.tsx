import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Layers,
  ScanLine,
  TrendingUp,
  Cpu,
  GraduationCap
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/batches', label: 'Incubation Batches', icon: Layers },
    { to: '/scans', label: 'Scan Explorer', icon: ScanLine },
    { to: '/analytics', label: 'Hatchery Analytics', icon: TrendingUp },
    { to: '/devices', label: 'Edge Stations (IoT)', icon: Cpu },
  ];

  return (
    <aside className="w-64 bg-[#1E293B] border-r border-slate-800 flex flex-col justify-between shrink-0 shadow-lg min-h-[calc(100vh-4rem)]">
      {/* Navigation Links */}
      <div className="p-4 space-y-1.5">
        <p className="px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Management Portal
        </p>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-[#800000] text-white shadow-md font-semibold border-l-4 border-amber-400'
                  : 'text-slate-300 hover:bg-slate-800/80 hover:text-slate-100'
              }`
            }
          >
            <item.icon className="w-4 h-4 shrink-0" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>

      {/* Institutional Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/40">
        <div className="flex items-center gap-2.5 p-2 rounded-lg bg-slate-800/60 border border-slate-700/50">
          <GraduationCap className="w-5 h-5 text-amber-400 shrink-0" />
          <div className="text-[11px]">
            <p className="font-bold text-slate-200">BSIT Capstone 2026</p>
            <p className="text-slate-400">Foundation University</p>
          </div>
        </div>
      </div>
    </aside>
  );
};
