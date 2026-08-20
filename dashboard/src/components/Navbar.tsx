import React, { useState, useEffect } from 'react';
import { ShieldCheck, Activity, Clock, Cpu, Bell, Layers } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString('en-US', { hour12: false }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="bg-obsidian-900 border-b border-obsidian-700/80 px-4 md:px-6 py-2.5 flex items-center justify-between sticky top-0 z-50">
      {/* Brand & Capstone Identification */}
      <div className="flex items-center gap-3">
        {/* Foundation University Maroon Insignia */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-[#800000] border border-[#991B1B] flex items-center justify-center text-amber-300 font-display font-black text-base shadow-md">
            OL
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-display font-bold tracking-wider text-slate-100 uppercase">
                OvaLens
              </h1>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 bg-[#800000]/30 border border-[#800000] text-amber-300 rounded">
                v2.0 SCADA
              </span>
            </div>
            <p className="text-[10px] font-mono text-slate-400">
              Foundation University Duck Hatchery Terminal
            </p>
          </div>
        </div>
      </div>

      {/* Industrial Telemetry Indicators */}
      <div className="flex items-center gap-3 md:gap-5 text-xs font-mono">
        {/* Active Station Indicator */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-obsidian-850 border border-obsidian-700 rounded text-slate-300">
          <Cpu className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-[11px]">STATION: <strong className="text-slate-100">STATION-01-RP5</strong></span>
        </div>

        {/* Backend Heartbeat */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-950/60 border border-emerald-700/50 rounded text-emerald-300">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-led-pulse shadow-[0_0_6px_#10B981]" />
          <span className="text-[11px] font-bold">API: 12ms (ONLINE)</span>
        </div>

        {/* Real-time System Clock */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 bg-obsidian-850 border border-obsidian-700 rounded text-slate-300">
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-[11px] text-amber-300 font-bold">{timeStr || '00:00:00'} PHT</span>
        </div>

        {/* System Operator Profile */}
        <div className="flex items-center gap-2 pl-2 border-l border-obsidian-700/80">
          <div className="w-7 h-7 rounded bg-obsidian-800 border border-obsidian-600 flex items-center justify-center text-xs font-mono font-bold text-amber-300">
            OP
          </div>
          <div className="hidden lg:block text-left text-[10px]">
            <span className="font-bold text-slate-200 block">Operator Lead</span>
            <span className="text-emerald-400">SESSION ACTIVE</span>
          </div>
        </div>
      </div>
    </header>
  );
};
