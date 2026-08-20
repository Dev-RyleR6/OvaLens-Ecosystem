import React, { useState, useEffect } from 'react';
import { LogOut, Loader2, X } from 'lucide-react';

interface LogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void> | void;
  userName?: string;
}

export const LogoutModal: React.FC<LogoutModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  userName,
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-[2px] transition-opacity animate-in fade-in-50 duration-150"
        onClick={() => {
          if (!isLoggingOut) onClose();
        }}
      />

      {/* Dialog Box */}
      <div className="relative w-full max-w-sm bg-white rounded-2xl p-6 shadow-xl border border-slate-200/90 z-10 animate-in fade-in-50 zoom-in-95 duration-150 font-sans">
        
        {/* Close Button */}
        <button
          type="button"
          disabled={isLoggingOut}
          onClick={onClose}
          className="absolute right-4 top-4 text-slate-400 hover:text-slate-600 hover:bg-slate-100 p-1.5 rounded-lg transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Icon & Heading */}
        <div className="flex items-start gap-3.5 mb-4">
          <div className="w-10 h-10 rounded-xl bg-red-50 text-red-600 border border-red-100 flex items-center justify-center shrink-0">
            <LogOut className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900 leading-tight">
              Sign out of OvaLens?
            </h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              {userName ? `Logging out as ${userName}.` : 'You will be returned to the login screen.'} All conveyor records remain securely saved.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2 mt-6 pt-3 border-t border-slate-100">
          <button
            type="button"
            disabled={isLoggingOut}
            onClick={onClose}
            className="py-2 px-3.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-xl transition-colors cursor-pointer disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isLoggingOut}
            onClick={handleConfirm}
            className="py-2 px-4 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 active:bg-red-800 rounded-xl transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-xs disabled:opacity-60"
          >
            {isLoggingOut ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Signing out...</span>
              </>
            ) : (
              <span>Sign Out</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LogoutModal;
