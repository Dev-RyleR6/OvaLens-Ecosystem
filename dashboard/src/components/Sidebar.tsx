import React, { useState } from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Layers,
  ScanLine,
  TrendingUp,
  Cpu,
  Sparkles,
  Bot,
  Settings,
  HelpCircle,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  HardDrive,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SidebarProps {
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean | ((prev: boolean) => boolean)) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isCollapsed, setIsCollapsed }) => {
  const [openSections, setOpenSections] = useState({
    main: true,
    features: true,
    tools: true,
  });
  const [isSyncing, setIsSyncing] = useState(false);

  const toggleSection = (section: 'main' | 'features' | 'tools') => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const handleManualSync = () => {
    setIsSyncing(true);
    setTimeout(() => setIsSyncing(false), 800);
  };

  return (
    <aside
      className={cn(
        "border-r border-[#1F2636] bg-[#0B0D13] flex flex-col justify-between transition-all duration-200 flex-shrink-0 z-30 overflow-y-auto select-none",
        isCollapsed ? "w-16" : "w-60"
      )}
    >
      <div className="p-3.5 space-y-5">
        {/* Brand Header */}
        <div className="flex items-center justify-between px-2 pt-1">
          <div className="flex items-center gap-2.5">
            {/* Logo Glyph */}
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#800000] to-rose-600 flex items-center justify-center text-white shadow-lg shadow-[#800000]/30 font-bold text-sm">
              ∞
            </div>
            {!isCollapsed && (
              <div>
                <span className="font-bold text-sm text-slate-100 tracking-tight block leading-tight">
                  OvaLens
                </span>
                <span className="text-[10px] text-slate-400 font-medium">Hatchery AI</span>
              </div>
            )}
          </div>

          <button
            onClick={() => setIsCollapsed(prev => !prev)}
            className="p-1 rounded-lg hover:bg-[#161B27] text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
            title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Section 1: MAIN */}
        <div className="space-y-1">
          {!isCollapsed && (
            <button
              onClick={() => toggleSection('main')}
              className="w-full flex items-center justify-between px-2.5 py-1 text-[11px] font-semibold text-slate-500 uppercase tracking-wider hover:text-slate-300 transition-colors"
            >
              <span>Main</span>
              <ChevronDown className={cn("w-3.5 h-3.5 transition-transform", !openSections.main && "-rotate-90")} />
            </button>
          )}

          {(openSections.main || isCollapsed) && (
            <div className="space-y-0.5 pt-0.5">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all group",
                    isActive
                      ? "bg-gradient-to-r from-teal-500/20 to-emerald-500/10 text-emerald-300 border border-teal-500/30 shadow-inner font-semibold"
                      : "text-slate-400 hover:text-slate-200 hover:bg-[#161B27]"
                  )
                }
                title={isCollapsed ? "Overview" : undefined}
              >
                <LayoutDashboard className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                {!isCollapsed && <span>Overview</span>}
              </NavLink>

              <NavLink
                to="/batches"
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all group",
                    isActive
                      ? "bg-gradient-to-r from-teal-500/20 to-emerald-500/10 text-emerald-300 border border-teal-500/30 font-semibold"
                      : "text-slate-400 hover:text-slate-200 hover:bg-[#161B27]"
                  )
                }
                title={isCollapsed ? "Batches" : undefined}
              >
                <Layers className="w-4 h-4 flex-shrink-0" />
                {!isCollapsed && <span>Incubation Batches</span>}
              </NavLink>

              <NavLink
                to="/scans"
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all group",
                    isActive
                      ? "bg-gradient-to-r from-teal-500/20 to-emerald-500/10 text-emerald-300 border border-teal-500/30 font-semibold"
                      : "text-slate-400 hover:text-slate-200 hover:bg-[#161B27]"
                  )
                }
                title={isCollapsed ? "Scan Explorer" : undefined}
              >
                <ScanLine className="w-4 h-4 flex-shrink-0" />
                {!isCollapsed && <span>Scan Explorer</span>}
              </NavLink>

              <NavLink
                to="/analytics"
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all group",
                    isActive
                      ? "bg-gradient-to-r from-teal-500/20 to-emerald-500/10 text-emerald-300 border border-teal-500/30 font-semibold"
                      : "text-slate-400 hover:text-slate-200 hover:bg-[#161B27]"
                  )
                }
                title={isCollapsed ? "Economics & ROI" : undefined}
              >
                <TrendingUp className="w-4 h-4 flex-shrink-0" />
                {!isCollapsed && <span>Economics & Yield</span>}
              </NavLink>

              <NavLink
                to="/devices"
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all group",
                    isActive
                      ? "bg-gradient-to-r from-teal-500/20 to-emerald-500/10 text-emerald-300 border border-teal-500/30 font-semibold"
                      : "text-slate-400 hover:text-slate-200 hover:bg-[#161B27]"
                  )
                }
                title={isCollapsed ? "Edge Devices" : undefined}
              >
                <Cpu className="w-4 h-4 flex-shrink-0" />
                {!isCollapsed && <span>Edge Sorter Nodes</span>}
              </NavLink>
            </div>
          )}
        </div>

        {/* Section 2: FEATURES */}
        {!isCollapsed && (
          <div className="space-y-1">
            <button
              onClick={() => toggleSection('features')}
              className="w-full flex items-center justify-between px-2.5 py-1 text-[11px] font-semibold text-slate-500 uppercase tracking-wider hover:text-slate-300 transition-colors"
            >
              <span>Features</span>
              <ChevronDown className={cn("w-3.5 h-3.5 transition-transform", !openSections.features && "-rotate-90")} />
            </button>

            {openSections.features && (
              <div className="space-y-0.5 pt-0.5">
                <Link
                  to="/analytics"
                  className="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-[#161B27] transition-all"
                >
                  <Sparkles className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                  <span>AI Candling Insights</span>
                </Link>

                <a
                  href="#copilot-chat"
                  className="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-[#161B27] transition-all"
                >
                  <Bot className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <span>Hatchery Copilot</span>
                </a>
              </div>
            )}
          </div>
        )}

        {/* Section 3: TOOLS */}
        {!isCollapsed && (
          <div className="space-y-1">
            <button
              onClick={() => toggleSection('tools')}
              className="w-full flex items-center justify-between px-2.5 py-1 text-[11px] font-semibold text-slate-500 uppercase tracking-wider hover:text-slate-300 transition-colors"
            >
              <span>Tools</span>
              <ChevronDown className={cn("w-3.5 h-3.5 transition-transform", !openSections.tools && "-rotate-90")} />
            </button>

            {openSections.tools && (
              <div className="space-y-0.5 pt-0.5">
                <Link
                  to="/devices"
                  className="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-[#161B27] transition-all"
                >
                  <Settings className="w-4 h-4 flex-shrink-0" />
                  <span>Calibration Settings</span>
                </Link>

                <Link
                  to="/batches"
                  className="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-[#161B27] transition-all"
                >
                  <HelpCircle className="w-4 h-4 flex-shrink-0" />
                  <span>Hatchery Guide</span>
                </Link>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Sync Callout Card (like "Upgrade to Pro" in reference) */}
      {!isCollapsed && (
        <div className="p-3.5 m-3 rounded-2xl bg-gradient-to-b from-[#161E2E] to-[#111622] border border-[#222E46] space-y-2.5 shadow-lg">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-teal-500/20 text-teal-300">
              <HardDrive className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-bold text-slate-100 block">Edge Sync Engine</span>
              <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                SQLite WAL 100% Synced
              </span>
            </div>
          </div>

          <p className="text-[11px] text-slate-400 leading-snug">
            All candling scans continuously backed up to FastAPI + PostgreSQL.
          </p>

          <button
            onClick={handleManualSync}
            disabled={isSyncing}
            className="w-full h-8 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-600 hover:from-teal-400 hover:to-emerald-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 shadow-md shadow-teal-500/20 transition-all cursor-pointer"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", isSyncing && "animate-spin")} />
            <span>{isSyncing ? "Syncing..." : "Sync Edge Buffer"}</span>
          </button>
        </div>
      )}
    </aside>
  );
};
