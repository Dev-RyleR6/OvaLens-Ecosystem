import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Layers,
  ScanLine,
  TrendingUp,
  Cpu,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './ui/button';

interface SidebarProps {
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean | ((prev: boolean) => boolean)) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isCollapsed, setIsCollapsed }) => {
  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/batches', label: 'Batches', icon: Layers },
    { to: '/scans', label: 'Scan Explorer', icon: ScanLine },
    { to: '/analytics', label: 'Economics & ROI', icon: TrendingUp },
    { to: '/devices', label: 'Devices', icon: Cpu },
  ];

  return (
    <aside
      className={cn(
        "border-r bg-background flex flex-col justify-between transition-all duration-200 flex-shrink-0 z-30",
        isCollapsed ? "w-14" : "w-56"
      )}
    >
      {/* Navigation items */}
      <div className="p-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors group",
                  isActive
                    ? "bg-maroon-50 text-[#800000] dark:bg-maroon-950/40 dark:text-maroon-200 font-semibold"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
                )
              }
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {!isCollapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          );
        })}
      </div>

      {/* Collapse Toggle Footer */}
      <div className="p-2 border-t flex items-center justify-between">
        {!isCollapsed && (
          <span className="text-[11px] text-muted-foreground px-2">
            OvaLens v2.0
          </span>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsCollapsed((prev) => !prev)}
          className="h-8 w-8 ml-auto text-muted-foreground hover:text-foreground"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </Button>
      </div>
    </aside>
  );
};
