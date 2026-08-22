import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { useModalAnimation } from '@/hooks/useModalAnimation';
import { cn } from '@/lib/utils';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  maxWidth?: string;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  maxWidth = 'max-w-xl',
}) => {
  const { shouldRender, isClosing } = useModalAnimation(isOpen, 220);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!shouldRender) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* High-Contrast Dark Backdrop Blur */}
      <div
        className={cn(
          "fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity",
          isClosing ? "animate-modal-backdrop-exit" : "animate-modal-backdrop"
        )}
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div
        className={cn(
          `relative w-full ${maxWidth} bg-white border border-slate-200 rounded-xl shadow-2xl overflow-hidden z-10`,
          isClosing ? "animate-modal-content-exit" : "animate-modal-content"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-slate-50 border-b border-slate-200">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#800000]" />
            {title}
          </h3>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 max-h-[80vh] overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
};
