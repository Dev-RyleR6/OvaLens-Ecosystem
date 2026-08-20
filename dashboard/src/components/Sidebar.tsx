import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Layers,
  ScanLine,
  TrendingUp,
  Cpu,
  Microscope,
  Users,
  FileText,
  Settings,
  Archive,
  HardDrive,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export const Sidebar: React.FC = () => {
  const operationsNav = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/batches', label: 'Incubation Batches', icon: Layers },
    { to: '/scans', label: 'Candling Scans', icon: ScanLine },
    { to: '/analytics', label: 'Economics & Salvage', icon: TrendingUp },
    { to: '/devices', label: 'Edge Sorter Nodes', icon: Cpu },
  ];

  const adminNav = [
    { to: '/records', label: 'Historical Records', icon: Archive },
    { to: '/models', label: 'Vision Model (ONNX)', icon: Microscope },
    { to: '/users', label: 'User & Access', icon: Users },
    { to: '/logs', label: 'Audit Trail Logs', icon: FileText },
    { to: '/settings', label: 'Hatchery Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-[#E2E8F0] bg-white flex flex-col justify-between flex-shrink-0 z-30 h-full overflow-y-auto">
      {/* Navigation List */}
      <div className="p-4 space-y-5">
        {/* Operations Section */}
        <div className="space-y-1">
          <p className="px-3 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Operations Command
          </p>

          {operationsNav.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold transition-colors btn-press",
                    isActive
                      ? "bg-[#800000] text-white shadow-xs"
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

        {/* Administration Section */}
        <div className="space-y-1">
          <p className="px-3 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Administration & Archives
          </p>

          {adminNav.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold transition-colors btn-press",
                    isActive
                      ? "bg-[#800000] text-white shadow-xs"
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
      </div>

      {/* Bottom Hardware Status Card */}
      <div className="p-3.5 m-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HardDrive className="w-3.5 h-3.5 text-slate-700" />
            <span className="text-xs font-bold text-slate-800">Station-01-RP5</span>
          </div>
          <span className="inline-flex items-center gap-1.5 text-[11px] font-bold text-emerald-700">
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
