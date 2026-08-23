import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, LogOut, ShieldCheck, Server, Settings, User, ChevronDown, Sliders } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { LogoutModal } from './LogoutModal';
import { apiClient } from '../api/client';

interface NavbarProps {
  onToggleSidebar?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleSidebar }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isApiOnline, setIsApiOnline] = useState(true);
  const [currentTime, setCurrentTime] = useState<string>('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }));
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const checkBackend = async () => {
      const healthy = await apiClient.checkHealth();
      setIsApiOnline(healthy);
    };
    checkBackend();
    const interval = setInterval(checkBackend, 10000);
    return () => clearInterval(interval);
  }, []);

  // Close dropdown on click outside or escape key
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const getInitials = (name?: string) => {
    if (!name) return 'OP';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  const handleNavigate = (path: string) => {
    setIsDropdownOpen(false);
    navigate(path);
  };

  return (
    <>
      <header className="h-16 border-b border-[#E2E8F0] bg-white px-4 sm:px-6 flex items-center justify-between sticky top-0 z-40 shadow-2xs">
        {/* Left: Mobile Toggle & University Brand */}
        <div className="flex items-center gap-3">
          {/* Mobile Hamburger Toggle */}
          <button
            onClick={onToggleSidebar}
            className="lg:hidden p-2 rounded-lg text-slate-600 hover:text-[#800000] hover:bg-slate-100 transition-colors btn-press cursor-pointer"
            aria-label="Toggle Mobile Menu"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#800000] text-white flex items-center justify-center font-black text-sm tracking-tight shadow-xs flex-shrink-0">
              FU
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-[#0F172A] tracking-tight">
                  OvaLens
                </span>
                <span className="text-slate-300 text-xs hidden xs:inline">|</span>
                <span className="text-xs font-semibold text-slate-700 hidden sm:inline">
                  Foundation University Hatchery Portal
                </span>
              </div>
              <p className="text-[11px] text-slate-500 hidden md:block">
                Automated Duck Egg Candling & Incubation Management
              </p>
            </div>
          </div>
        </div>

        {/* Right Controls: Clock, Connection Indicators & User Profile Dropdown */}
        <div className="flex items-center gap-3">
          {/* Real-time Clock */}
          {currentTime && (
            <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 text-[11px] font-mono text-slate-600">
              <span className="w-1.5 h-1.5 rounded-full bg-[#800000] animate-pulse" />
              <span>{currentTime} PST</span>
            </div>
          )}

          {/* Live Backend Connection Indicator */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
            <span className={`w-2 h-2 rounded-full ${isApiOnline ? 'bg-emerald-600 animate-pulse' : 'bg-amber-500'}`} />
            <span className="font-medium text-slate-600">FastAPI Backend:</span>
            <span className={`font-bold ${isApiOnline ? 'text-emerald-700' : 'text-amber-700'}`}>
              {isApiOnline ? 'Connected' : 'Offline'}
            </span>
          </div>

          {/* Offline-First Edge Sync Pill */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            <span className="font-medium text-slate-600">Edge SQLite WAL:</span>
            <span className="font-bold text-slate-900">Synced</span>
          </div>

          {/* Merged User Profile Dropdown Menu */}
          <div className="relative pl-2 sm:pl-3 border-l border-slate-200" ref={dropdownRef}>
            <button
              onClick={() => setIsDropdownOpen(prev => !prev)}
              className={`flex items-center gap-2.5 p-1.5 rounded-xl transition-all cursor-pointer border ${
                isDropdownOpen
                  ? 'bg-slate-100/80 border-slate-300 shadow-xs'
                  : 'hover:bg-slate-50 border-transparent hover:border-slate-200'
              }`}
              aria-expanded={isDropdownOpen}
              aria-haspopup="true"
            >
              <div className="w-8 h-8 rounded-full bg-slate-100 text-[#800000] border border-slate-200 flex items-center justify-center text-xs font-bold shadow-2xs">
                {getInitials(user?.full_name)}
              </div>
              <div className="hidden md:block text-left">
                <div className="flex items-center gap-1.5">
                  <p className="text-xs font-bold text-[#0F172A] leading-tight">
                    {user?.full_name || 'Ryle Gabotero'}
                  </p>
                  <span className="text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded bg-red-50 text-[#800000] border border-red-200">
                    {user?.role || 'ADMIN'}
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 font-medium">
                  {user?.email || 'admin@foundationu.com'}
                </p>
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180 text-slate-700' : ''}`} />
            </button>

            {/* Dropdown Popover Menu */}
            {isDropdownOpen && (
              <div className="absolute right-0 mt-2 w-64 bg-white border border-slate-200 rounded-xl shadow-xl p-1.5 z-50 animate-in fade-in zoom-in-95 duration-150">
                {/* User Identity Header */}
                <div className="px-3 py-2.5 bg-slate-50/80 rounded-lg border border-slate-100 mb-1">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs font-bold text-slate-900 truncate">
                      {user?.full_name || 'Ryle Gabotero'}
                    </p>
                    <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-red-50 text-[#800000] border border-red-200">
                      {user?.role || 'ADMIN'}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 font-mono truncate">
                    {user?.email || 'admin@foundationu.com'}
                  </p>
                </div>

                {/* Menu Action Items */}
                <div className="space-y-0.5 text-xs font-medium text-slate-700">
                  <button
                    onClick={() => handleNavigate('/settings?tab=account')}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-100 hover:text-[#800000] transition-colors text-left cursor-pointer"
                  >
                    <User className="w-4 h-4 text-slate-500" />
                    <span>My Profile & Password</span>
                  </button>

                  <button
                    onClick={() => handleNavigate('/settings?tab=facility')}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-100 hover:text-[#800000] transition-colors text-left cursor-pointer"
                  >
                    <Settings className="w-4 h-4 text-slate-500" />
                    <span>Facility & System Settings</span>
                  </button>

                  <button
                    onClick={() => handleNavigate('/settings?tab=backups')}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-100 hover:text-[#800000] transition-colors text-left cursor-pointer"
                  >
                    <Database className="w-4 h-4 text-slate-500" />
                    <span>Database Backups</span>
                  </button>

                  <button
                    onClick={() => handleNavigate('/settings?tab=preferences')}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-100 hover:text-[#800000] transition-colors text-left cursor-pointer"
                  >
                    <Sliders className="w-4 h-4 text-slate-500" />
                    <span>UI & Alert Preferences</span>
                  </button>
                </div>

                <div className="h-px bg-slate-100 my-1" />

                {/* Sign Out Trigger */}
                <button
                  onClick={() => {
                    setIsDropdownOpen(false);
                    setShowLogoutModal(true);
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-rose-700 hover:bg-rose-50 hover:text-rose-800 transition-colors text-left text-xs font-semibold cursor-pointer"
                >
                  <LogOut className="w-4 h-4 text-rose-600" />
                  <span>Sign Out</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Logout Confirmation Prompt Modal */}
      <LogoutModal
        isOpen={showLogoutModal}
        onClose={() => setShowLogoutModal(false)}
        onConfirm={logout}
        user={user}
      />
    </>
  );
};
