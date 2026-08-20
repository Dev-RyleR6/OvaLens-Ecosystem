import React from 'react';
import { Sun, Moon, User, CheckCircle2 } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { Button } from './ui/button';

interface NavbarProps {
  sidebarOpen: boolean;
  setSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

export const Navbar: React.FC<NavbarProps> = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-14 border-b bg-background px-4 sm:px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Brand Identity & Title */}
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 rounded-md bg-[#800000] text-white flex items-center justify-center font-bold text-xs shadow-xs">
          OL
        </div>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm tracking-tight text-foreground">
            OvaLens
          </span>
          <span className="text-muted-foreground text-xs hidden sm:inline">/</span>
          <span className="text-muted-foreground text-xs hidden sm:inline">
            Foundation University Hatchery
          </span>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Subtle System Status */}
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span>System Online</span>
        </div>

        {/* Theme Toggle Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="h-8 w-8 text-muted-foreground hover:text-foreground"
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} mode`}
        >
          {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
          <span className="sr-only">Toggle theme</span>
        </Button>

        {/* User profile */}
        <div className="flex items-center gap-2 pl-2 border-l">
          <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground">
            <User className="w-3.5 h-3.5" />
          </div>
          <div className="hidden md:block text-left">
            <p className="text-xs font-medium leading-none text-foreground">Admin</p>
            <p className="text-[10px] text-muted-foreground">Hatchery Manager</p>
          </div>
        </div>
      </div>
    </header>
  );
};
