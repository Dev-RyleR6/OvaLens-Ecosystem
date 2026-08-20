import React, { useState, useEffect } from 'react';
import { FileText, Clock, Search, Bell, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Navbar: React.FC = () => {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const time = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
      const day = now.toLocaleDateString('en-US', { weekday: 'short' });
      setTimeStr(`${time}, ${day}`);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 px-4 sm:px-6 flex items-center justify-between gap-4 border-b border-[#1F2636] bg-[#0B0D13]/90 backdrop-blur-md sticky top-0 z-40">
      {/* Left Pill Controls */}
      <div className="flex items-center gap-2.5">
        <Link
          to="/batches"
          className="pill-button hover:border-emerald-500/40 hover:text-emerald-300"
        >
          <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_#10B981]" />
          <span>Reports & Audits</span>
        </Link>

        <div className="hidden sm:flex pill-button">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>{timeStr || '12:37 PM, Wed'}</span>
        </div>
      </div>

      {/* Center/Right: Global Search Bar */}
      <div className="flex-1 max-w-md hidden md:block">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search for any hatchery metrics, scans, batches..."
            className="w-full h-9 pl-9 pr-4 text-xs bg-[#121620] border border-[#1F2636] rounded-full text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/40 transition-all"
          />
        </div>
      </div>

      {/* Right Controls: Notifications & User Avatar */}
      <div className="flex items-center gap-3">
        {/* Notification Pill with unread badge */}
        <button
          className="relative p-2 rounded-full bg-[#121620] hover:bg-[#161B27] border border-[#1F2636] text-slate-300 transition-colors cursor-pointer"
          title="3 Active Batch Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_6px_#F59E0B]" />
        </button>

        {/* User Profile Avatar with Name & Role */}
        <div className="flex items-center gap-2.5 pl-1.5 cursor-pointer group">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#800000] via-rose-700 to-amber-500 p-[1.5px] shadow-md">
            <div className="w-full h-full rounded-full bg-[#121620] flex items-center justify-center text-xs font-bold text-amber-300">
              RG
            </div>
          </div>
          <div className="hidden lg:block text-left">
            <p className="text-xs font-semibold leading-none text-slate-200 group-hover:text-white transition-colors">
              Ryle Gabotero
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Lead Hatchery Op</p>
          </div>
        </div>
      </div>
    </header>
  );
};
