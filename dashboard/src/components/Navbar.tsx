import { usePreferences } from '../hooks/usePreferences';
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, LogOut, Server, Settings, User, ChevronDown, SlidersHorizontal, Menu } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { LogoutModal } from './LogoutModal';
import { apiClient } from '../api/client';
import { Badge } from './Badge';
import ovalensLogo from '../assets/logos/ovalens_logo_final.svg';

interface NavbarProps {
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleSidebar, sidebarOpen = false }) => {
  const { user, logout } = useAuth();
  const { pollingInterval } = usePreferences();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isApiOnline, setIsApiOnline] = useState<boolean | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    const checkBackend = async () => {
      const healthy = await apiClient.checkHealth();
      if (active) setIsApiOnline(healthy);
    };
    void checkBackend();
    const interval = pollingInterval > 0 ? setInterval(checkBackend, pollingInterval * 1000) : undefined;
    return () => { active = false; clearInterval(interval); };
  }, [pollingInterval]);

  useEffect(() => {
    if (!isDropdownOpen) return;
    menuRef.current?.querySelector<HTMLButtonElement>('button')?.focus();
    const outside = (event: PointerEvent) => {
      if (!dropdownRef.current?.contains(event.target as Node)) setIsDropdownOpen(false);
    };
    document.addEventListener('pointerdown', outside);
    return () => document.removeEventListener('pointerdown', outside);
  }, [isDropdownOpen]);

  const getInitials = (name?: string) => {
    const parts = name?.replace(/\([^)]*\)/g, '').trim().split(/\s+/).filter(Boolean) ?? [];
    return parts.length > 1 ? `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase() : (parts[0]?.slice(0, 2).toUpperCase() || 'OP');
  };

  const handleNavigate = (path: string) => {
    setIsDropdownOpen(false);
    navigate(path);
  };

  const handleMenuKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      setIsDropdownOpen(false);
      triggerRef.current?.focus();
    }
    if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      const buttons = Array.from(menuRef.current?.querySelectorAll<HTMLButtonElement>('button') ?? []);
      const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
      buttons[next]?.focus();
    }
  };
  const menuAction = 'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-slate-100 hover:text-brand transition-colors text-left text-sm';

  return <>
    <header className="h-16 shrink-0 border-b border-border bg-card px-3 sm:px-6 flex items-center justify-between gap-3 sticky top-0 z-40">
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <button onClick={onToggleSidebar} className="lg:hidden flex items-center justify-center h-11 w-11 rounded-lg text-slate-600 hover:text-brand hover:bg-slate-100" aria-label={sidebarOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={sidebarOpen} aria-controls="dashboard-navigation">
          <Menu className="w-5 h-5" aria-hidden="true" />
        </button>
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-lg bg-[#F8FAFC] flex items-center justify-center shrink-0"><img src={ovalensLogo} alt="OvaLens logo" className="w-9 h-9 object-contain" width={36} height={36} /></div>
          <div className="min-w-0"><span className="font-semibold text-base text-foreground">OvaLens</span><p className="text-xs text-slate-500 hidden sm:block">Foundation University · Hatchery management</p></div>
        </div>
      </div>
      <div className="flex items-center gap-2 sm:gap-4 shrink-0">
        <div className="flex items-center gap-2 text-xs" role="status" aria-label={`Backend API: ${isApiOnline === null ? 'Checking' : isApiOnline ? 'Connected' : 'Unavailable'}`}>
          <Server className={`w-4 h-4 ${isApiOnline === null ? 'text-slate-500' : isApiOnline ? 'text-agri-green' : 'text-amber-700'}`} aria-hidden="true" />
          <span className="hidden md:inline text-slate-600">Backend API</span>
          <span className={`hidden sm:inline font-medium ${isApiOnline === null ? 'text-slate-500' : isApiOnline ? 'text-agri-green' : 'text-amber-700'}`}>{isApiOnline === null ? 'Checking…' : isApiOnline ? 'Connected' : 'Unavailable'}</span>
        </div>
        <div className="relative sm:pl-4 sm:border-l border-border" ref={dropdownRef} onKeyDown={handleMenuKeyDown} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setIsDropdownOpen(false); }}>
          <button ref={triggerRef} onClick={() => setIsDropdownOpen(prev => !prev)} className={`flex items-center gap-2 rounded-lg p-1.5 transition-colors ${isDropdownOpen ? 'bg-slate-100' : 'hover:bg-slate-50'}`} aria-expanded={isDropdownOpen} aria-controls="account-menu" aria-label="Open account menu">
            <span className="w-8 h-8 rounded-full bg-slate-100 text-brand border border-border flex items-center justify-center text-xs font-semibold shrink-0">{getInitials(user?.full_name)}</span>
            <span className="hidden xl:block text-left max-w-48"><span className="block text-sm font-medium truncate">{user?.full_name || 'Hatchery staff'}</span><span className="block text-xs text-slate-500 capitalize">{user?.role?.toLowerCase() || 'Operator'}</span></span>
            <ChevronDown className={`w-4 h-4 text-slate-500 ${isDropdownOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
          </button>
          {isDropdownOpen && <div ref={menuRef} id="account-menu" aria-label="Account actions" className="absolute right-0 mt-2 w-72 max-w-[calc(100vw-2rem)] bg-card rounded-xl shadow-xl p-2 z-50">
            <div className="px-3 py-3 border-b border-border mb-1"><p className="font-medium break-words">{user?.full_name || 'Hatchery staff'}</p><p className="text-xs text-slate-500 break-all mt-1">{user?.email || 'Email unavailable'}</p><div className="mt-2"><Badge type="role" value={user?.role || 'OPERATOR'} /></div></div>
            <div className="text-slate-700">
              <button onClick={() => handleNavigate('/settings?tab=account')} className={menuAction}><User className="w-4 h-4 shrink-0" aria-hidden="true" />Profile & password</button>
              {user?.role !== 'OPERATOR' && <button onClick={() => handleNavigate('/settings?tab=facility')} className={menuAction}><Settings className="w-4 h-4 shrink-0" aria-hidden="true" />Facility settings</button>}
              {user?.role !== 'OPERATOR' && <button onClick={() => handleNavigate('/settings?tab=backups')} className={menuAction}><Database className="w-4 h-4 shrink-0" aria-hidden="true" />Database backups</button>}
              <button onClick={() => handleNavigate('/settings?tab=preferences')} className={menuAction}><SlidersHorizontal className="w-4 h-4 shrink-0" aria-hidden="true" />Display preferences</button>
            </div>
            <div className="border-t border-border mt-1 pt-1"><button onClick={() => { setIsDropdownOpen(false); setShowLogoutModal(true); }} className={`${menuAction} text-red-700 hover:bg-red-50`}><LogOut className="w-4 h-4 shrink-0" aria-hidden="true" />Sign out</button></div>
          </div>}
        </div>
      </div>
    </header>
    <LogoutModal isOpen={showLogoutModal} onClose={() => setShowLogoutModal(false)} onConfirm={logout} user={user} />
  </>;
};
