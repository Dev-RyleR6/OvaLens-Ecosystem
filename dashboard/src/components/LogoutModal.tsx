import React, { useState, useEffect } from 'react';
import { LogOut, Loader2, X, CheckCircle2, Shield, User as UserIcon } from 'lucide-react';
import { User } from '../types';

interface LogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void> | void;
  user?: User | null;
}

export const LogoutModal: React.FC<LogoutModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  user,
}) => {
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isLoggingOut) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isLoggingOut, onClose]);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    setIsLoggingOut(true);
    try {
      await onConfirm();
    } finally {
      setIsLoggingOut(false);
      onClose();
    }
  };

  const getInitials = (name?: string) => {
    if (!name) return 'OP';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Soft Blurred Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/35 backdrop-blur-[3px] transition-opacity animate-in fade-in-50 duration-200"
        onClick={() => {
          if (!isLoggingOut) onClose();
        }}
      />

      {/* Main Dialog Card */}
      <div className="relative w-full max-w-md bg-white rounded-2xl p-6 sm:p-7 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.18)] border border-slate-200/90 z-10 animate-in fade-in-50 zoom-in-[0.98] duration-200 font-sans text-slate-900">
        
        {/* Top Close Button */}
        <button
          type="button"
          disabled={isLoggingOut}
          onClick={onClose}
          className="absolute right-4 top-4 text-slate-400 hover:text-slate-700 hover:bg-slate-100 p-1.5 rounded-lg transition-colors cursor-pointer disabled:opacity-40"
          title="Close dialog"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Dialog Header */}
        <div className="flex items-start gap-4 mb-5">
          <div className="w-11 h-11 rounded-2xl bg-red-50 text-red-700 border border-red-100 flex items-center justify-center shrink-0 shadow-xs">
            <LogOut className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900 tracking-tight">
              Sign Out of OvaLens
            </h3>
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
              Are you sure you want to end your current session?
            </p>
          </div>
        </div>

        {/* Current Active Session Preview Tile */}
        <div className="bg-slate-50/80 border border-slate-200/80 rounded-xl p-3.5 mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-white text-[#800000] border border-slate-200 font-bold text-xs flex items-center justify-center shadow-xs">
              {getInitials(user?.full_name)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <p className="text-xs font-bold text-slate-900 leading-tight">
                  {user?.full_name || 'Hatchery Lead'}
                </p>
                <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-slate-200/60 text-slate-700">
                  {user?.role || 'ADMIN'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium mt-0.5">
                {user?.email || 'admin@foundationu.com'}
              </p>
            </div>
          </div>
        </div>

        {/* Data Persistence Safety Notice */}
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-50/70 border border-emerald-100 text-[11px] text-emerald-800 mb-6">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
          <span className="font-medium">
            Edge sorting records and live session data remain securely saved.
          </span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center justify-end gap-2.5">
          <button
            type="button"
            disabled={isLoggingOut}
            onClick={onClose}
            className="py-2.5 px-4 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 active:bg-slate-100 border border-slate-300 rounded-xl transition-all cursor-pointer disabled:opacity-50 active:scale-[0.98]"
          >
            Stay Signed In
          </button>
          
          <button
            type="button"
            disabled={isLoggingOut}
            onClick={handleConfirm}
            className="py-2.5 px-5 text-xs font-semibold text-white bg-[#800000] hover:bg-[#6b0000] active:bg-[#520000] rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-60 active:scale-[0.98]"
          >
            {isLoggingOut ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Signing out...</span>
              </>
            ) : (
              <>
                <LogOut className="w-3.5 h-3.5" />
                <span>Sign Out</span>
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
};

export default LogoutModal;
