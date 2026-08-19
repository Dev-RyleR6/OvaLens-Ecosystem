import React, { useState, useEffect } from 'react';
import { Shield, Clock, Wifi } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const update = () => {
      setTimeStr(new Date().toLocaleTimeString('en-US', { hour12: false }));
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 bg-[#1E293B] border-b border-slate-800 flex items-center justify-between px-6 sticky top-0 z-30 shadow-md">
      {/* Brand & Title */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-[#800000] text-white font-black text-sm shadow-md border border-[#991B1B]">
          FU
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold text-slate-100 tracking-tight">OvaLens Ecosystem</h1>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-[#800000]/40 text-amber-300 border border-[#800000]/60">
              Foundation University
            </span>
          </div>
          <p className="text-xs text-slate-400">Automated Duck Egg Candling & Hatchery Analytics</p>
        </div>
      </div>

      {/* Right Telemetry Indicators */}
      <div className="flex items-center gap-4">
        {/* Clock */}
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-md border border-slate-800 font-mono">
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          <span>{timeStr} PST</span>
        </div>

        {/* Edge Station Live Badge */}
        <div className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-md bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
          <Wifi className="w-3.5 h-3.5 animate-pulse" />
          <span className="hidden md:inline">Station-01</span> ONLINE
        </div>

        {/* User Pill */}
        <div className="flex items-center gap-2 pl-3 border-l border-slate-700">
          <div className="w-8 h-8 rounded-full bg-[#800000] text-white flex items-center justify-center text-xs font-bold ring-2 ring-[#991B1B]">
            JD
          </div>
          <div className="hidden lg:block text-left text-xs">
            <p className="font-semibold text-slate-200">Dr. Juan Dela Cruz</p>
            <p className="text-[10px] text-amber-400 font-medium flex items-center gap-1">
              <Shield className="w-2.5 h-2.5 inline" /> Hatchery Admin
            </p>
          </div>
        </div>
      </div>
    </header>
  );
};
