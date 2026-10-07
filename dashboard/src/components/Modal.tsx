import { CloseButton } from './ui/CloseButton';
import { useDialogAccessibility } from '@/hooks/useDialogAccessibility';
import React, { useEffect } from 'react';
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
  const dialogRef = useDialogAccessibility(isOpen && shouldRender, onClose, title);



  if (!shouldRender) return null;

  return (
    <div ref={dialogRef} className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
      {/* High-Contrast Dark Backdrop Blur */}
      <div
        className={cn(
          "fixed inset-0 bg-slate-900/65  transition-opacity",
          isClosing ? "animate-modal-backdrop-exit" : "animate-modal-backdrop"
        )}
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div
        className={cn(
          `relative w-full ${maxWidth} bg-card border border-slate-200/90 rounded-2xl shadow-2xl overflow-hidden z-10 my-auto max-h-[calc(100dvh-1.5rem)] sm:max-h-[88vh] flex flex-col`,
          isClosing ? "animate-modal-content-exit" : "animate-modal-content"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex-shrink-0">
          <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#800000]" />
            {title}
          </h3>
          <CloseButton aria-label="Close dialog" onClick={onClose} />
        </div>

        {/* Content Body */}
        <div className="p-4 sm:p-5 overflow-y-auto custom-scrollbar flex-1">
          {children}
        </div>
      </div>
    </div>
  );
};
