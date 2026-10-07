import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Layers, ScanLine, ChartNoAxesCombined, Cpu, Users, Settings, X, Radio, ChevronRight } from 'lucide-react';
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
    { to: '/analytics', label: 'Analytics', icon: ChartNoAxesCombined },
    { to: '/devices', label: 'Sorter devices', icon: Cpu },
    ...(user?.role === 'ADMIN' ? [{ to: '/users', label: 'Users & access', icon: Users }] : []),
    { to: user?.role === 'OPERATOR' ? '/settings?tab=account' : '/settings', label: user?.role === 'OPERATOR' ? 'My account' : 'Settings', icon: Settings },
  ];
  return (
    <div ref={dialogRef} className={`mobile-navigation ${isOpen ? 'is-open' : ''} lg:visible lg:relative lg:w-64 lg:shrink-0`} id="dashboard-navigation">
      {isOpen && mobile && <div className="fixed inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />}
      <aside className="hatchery-sidebar relative w-64 h-full flex flex-col">
        <div className="lg:hidden sidebar-mobile-header flex items-center justify-between p-4"><span className="font-semibold">Navigation</span><button onClick={onClose} aria-label="Close navigation"><X className="w-5 h-5" /></button></div>
        <div className="sidebar-identity"><span>OvaLens</span><p>Hatchery operations</p></div>
        <nav aria-label="Main navigation" className="px-3 pb-4 space-y-1 flex-1 overflow-y-auto">
          {links.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} onClick={onClose} className="nav-link"><Icon className="w-[18px] h-[18px] shrink-0" strokeWidth={1.75} aria-hidden="true" />{label}</NavLink>)}
        </nav>
        <div className="sidebar-connections p-4 space-y-2"><NavLink to="/devices" onClick={onClose} className="sidebar-connection-link action-link w-full text-sm"><Radio className="w-4 h-4" aria-hidden="true" />Edge app connections<ChevronRight className="w-4 h-4 ml-auto" aria-hidden="true" /></NavLink><p className="sidebar-status text-sm" role="status">{unavailable ? 'Edge status unavailable' : devices === null ? 'Checking edge apps…' : devices.length === 0 ? 'No edge apps registered' : `${reporting} of ${devices.length} edge apps online`}</p><p className="sidebar-note text-xs leading-relaxed">Checked every 15 seconds. Offline after 90 seconds without a heartbeat. Hardware readiness is checked at the edge.</p></div>
      </aside>
    </div>
  );
};
