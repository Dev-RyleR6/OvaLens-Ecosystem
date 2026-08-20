import React, { useState } from 'react';
import { Database, LogOut, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { LogoutModal } from './LogoutModal';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  const getInitials = (name?: string) => {
    if (!name) return 'OP';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <>
      <header className="h-16 border-b border-[#E2E8F0] bg-white px-6 flex items-center justify-between sticky top-0 z-40">
        {/* University Brand & Portal Title */}
        <div className="flex items-center gap-3.5">
          <div className="w-9 h-9 rounded-lg bg-[#800000] text-white flex items-center justify-center font-black text-sm tracking-tight shadow-xs">
            FU
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-[#0F172A] tracking-tight">
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
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            <span className="font-medium text-slate-600">Edge SQLite WAL:</span>
            <span className="font-bold text-slate-900">Synced</span>
          </div>

          {/* User Operator Profile */}
          <div className="flex items-center gap-2.5 pl-3 border-l border-slate-200">
            <div className="w-8 h-8 rounded-full bg-slate-100 text-[#800000] border border-slate-200 flex items-center justify-center text-xs font-bold">
              {getInitials(user?.full_name)}
            </div>
            <div className="hidden md:block text-left">
              <div className="flex items-center gap-1.5">
                <p className="text-xs font-bold text-[#0F172A] leading-tight">
                  {user?.full_name || 'Ryle Gabotero'}
                </p>
                <span className="text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded bg-slate-100 text-[#800000] border border-slate-200">
                  {user?.role || 'ADMIN'}
                </span>
              </div>
              <p className="text-[10px] text-slate-500 font-medium">
                {user?.email || 'admin@foundationu.com'}
              </p>
            </div>

            {/* Logout Button */}
            <button
              onClick={() => setShowLogoutModal(true)}
              className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors cursor-pointer ml-1"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Logout Confirmation Prompt Modal */}
      <LogoutModal
        isOpen={showLogoutModal}
        onClose={() => setShowLogoutModal(false)}
        onConfirm={logout}
        userName={user?.full_name}
      />
    </>
  );
};

