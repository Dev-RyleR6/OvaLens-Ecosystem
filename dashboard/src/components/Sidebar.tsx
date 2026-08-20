import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Layers,
  ScanLine,
  TrendingUp,
  Cpu,
  HelpCircle,
  HardDrive
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard, keyHint: '1' },
    { to: '/batches', label: 'Batches', icon: Layers, keyHint: '2' },
    { to: '/scans', label: 'Scan Explorer', icon: ScanLine, keyHint: '3' },
    { to: '/analytics', label: 'Economics & ROI', icon: TrendingUp, keyHint: '4' },
    { to: '/devices', label: 'IoT Stations', icon: Cpu, keyHint: '5' },
  ];

  return (
    <aside className="w-16 md:w-56 bg-obsidian-900 border-r border-obsidian-700/80 flex flex-col justify-between flex-shrink-0">
      <div className="p-3 space-y-1.5">
        <div className="hidden md:block px-3 py-2 text-[10px] font-mono font-bold tracking-widest text-slate-500 uppercase">
          NAVIGATION TERMINAL
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2.5 rounded text-xs font-medium transition-all group ${
                  isActive
                    ? 'bg-[#800000] text-white font-bold shadow-md border-l-4 border-amber-400'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-obsidian-800 border-l-4 border-transparent'
                }`
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span className="hidden md:inline font-display">{item.label}</span>
              </div>
              <span className="hidden md:inline text-[9px] font-mono opacity-60 group-hover:opacity-100 bg-black/30 px-1.5 py-0.5 rounded">
                [{item.keyHint}]
              </span>
            </NavLink>
          );
        })}
      </div>

      {/* Footer System Status Badge */}
      <div className="p-3 border-t border-obsidian-800">
        <div className="hidden md:flex items-center justify-between p-2.5 bg-obsidian-950/80 rounded border border-obsidian-800 text-[10px] font-mono">
          <div className="flex items-center gap-2">
            <HardDrive className="w-3.5 h-3.5 text-amber-400" />
            <div>
              <span className="text-slate-300 font-bold block">SQLite WAL</span>
              <span className="text-emerald-400">SYNC: 100% OK</span>
            </div>
          </div>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-led-pulse" />
        </div>
      </div>
    </aside>
  );
};
