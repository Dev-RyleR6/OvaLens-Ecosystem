import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Layers, ScanLine, TrendingUp, Cpu, Users, Settings, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { Device } from '../types';
import { useDialogAccessibility } from '../hooks/useDialogAccessibility';
import { deviceAvailability } from '../lib/deviceStatus';

interface SidebarProps { isOpen?: boolean; onClose?: () => void; }

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = false, onClose }) => {
  const { user } = useAuth();
  const [devices, setDevices] = useState<Device[] | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [now, setNow] = useState(Date.now);
  const [mobile, setMobile] = useState(() => window.matchMedia('(max-width: 1023px)').matches);
  const dialogRef = useDialogAccessibility(isOpen && mobile, () => onClose?.(), 'Navigation');
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    const media = window.matchMedia('(max-width: 1023px)');
    const update = () => setMobile(media.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    let active = true;
    const refresh = () => apiClient.getDevices().then(data => {
      if (active) { setDevices(data); setNow(Date.now()); setUnavailable(false); }
    }).catch(() => { if (active) setUnavailable(true); });
    void refresh();
    const timer = setInterval(() => { void refresh(); }, 15_000);
    return () => { active = false; clearInterval(timer); };
  }, []);
  const reporting = devices?.filter(device => ['ONLINE', 'SCANNING'].includes(deviceAvailability(device, now))).length ?? 0;
  const links = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/batches', label: 'Incubation batches', icon: Layers },
    { to: '/scans', label: 'Candling scans', icon: ScanLine },
    { to: '/analytics', label: 'Analytics & graphs', icon: TrendingUp },
    { to: '/devices', label: 'Sorter devices', icon: Cpu },
    ...(user?.role === 'ADMIN' ? [{ to: '/users', label: 'Users & access', icon: Users }] : []),
    { to: user?.role === 'OPERATOR' ? '/settings?tab=account' : '/settings', label: user?.role === 'OPERATOR' ? 'My account' : 'Settings', icon: Settings },
  ];
  return (
    <div ref={dialogRef} className={`mobile-navigation ${isOpen ? 'is-open' : ''} lg:visible lg:relative lg:w-60 lg:shrink-0`} id="dashboard-navigation">
      {isOpen && mobile && <div className="fixed inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />}
      <aside className="relative w-60 h-full border-r border-border bg-card flex flex-col">
        <div className="lg:hidden flex items-center justify-between p-4 border-b border-border"><span className="font-semibold">Navigation</span><button onClick={onClose} aria-label="Close navigation"><X className="w-5 h-5" /></button></div>
        <nav aria-label="Main navigation" className="p-3 space-y-1 flex-1 overflow-y-auto">
          {links.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} onClick={onClose} className={({ isActive }) => `flex items-center gap-3 px-3 py-3 rounded-lg ${isActive ? 'bg-maroon-50 text-brand font-semibold' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}><Icon className="w-4 h-4 shrink-0" aria-hidden="true" />{label}</NavLink>)}
        </nav>
        <div className="p-5 border-t border-border space-y-1"><NavLink to="/devices" onClick={onClose} className="font-medium text-brand underline underline-offset-4">Edge app connections</NavLink><p className="text-sm text-slate-600" role="status">{unavailable ? 'Edge status unavailable' : devices === null ? 'Checking edge apps…' : devices.length === 0 ? 'No edge apps registered' : `${reporting} of ${devices.length} edge apps online`}</p><p className="text-xs text-slate-500">Checked every 15 seconds. Offline after 90 seconds without a heartbeat. Hardware readiness is checked at the edge.</p></div>
      </aside>
    </div>
  );
};
