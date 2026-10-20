import { CloseButton } from './ui/CloseButton';
import { useDialogAccessibility } from '@/hooks/useDialogAccessibility';
import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react';
import { EggScan, FertilityClass } from '../types';
import { Badge } from './Badge';
import { useModalAnimation } from '@/hooks/useModalAnimation';
import { cn } from '@/lib/utils';

interface HumanInTheLoopOverrideModalProps {
  isOpen: boolean;
  scan: EggScan | null;
  targetClass: FertilityClass | null;
  onClose: () => void;
  onConfirm: (targetClass: FertilityClass, reason: string) => Promise<void>;
}

const REASON_PRESETS: Record<FertilityClass, string[]> = {
  FERTILE: [
    'Visual confirmation of active spider blood veins & dark embryo eye spot.',
    'Early vascular network detected on Day 10 re-candling.',
    'False negative: Optical shadowing masked blood vessels.',
  ],
  INFERTILE: [
    'Clear unfertilized yolk with no vascular development (Day 10 Penoy).',
    'Yolk mobility verified; salvageable as commercial Penoy @ ₱14.00.',
    'False positive: Yolk density misinterpreted as embryo.',
  ],
};

export const HumanInTheLoopOverrideModal: React.FC<HumanInTheLoopOverrideModalProps> = ({
  isOpen,
  scan,
  targetClass,
  onClose,
  onConfirm,
}) => {
  const lastScanRef = React.useRef(scan);
  const lastTargetClassRef = React.useRef(targetClass);
  if (scan) lastScanRef.current = scan;
  if (targetClass) lastTargetClassRef.current = targetClass;

  const displayScan = scan || lastScanRef.current;
  const displayTargetClass = targetClass || lastTargetClassRef.current;

  const [reason, setReason] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { shouldRender, isClosing } = useModalAnimation(isOpen, 220);
  const dialogRef = useDialogAccessibility(isOpen && shouldRender, () => { if (!isSubmitting) onClose(); }, 'Correct classification');

  useEffect(() => {
    if (displayTargetClass && REASON_PRESETS[displayTargetClass]?.length > 0) {
      setReason(REASON_PRESETS[displayTargetClass][0]);
    } else {
      setReason('Visual re-inspection by operator');
    }
    setError(null);
  }, [displayTargetClass, isOpen]);

  if (!shouldRender || !displayScan || !displayTargetClass) return null;

  const currentClass = displayScan.final_class || 'FERTILE';

  const handleSelectPreset = (preset: string) => {
    setReason(preset);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError('Please provide or select a justification for the audit trail.');
      return;
    }

    if (!displayTargetClass) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await onConfirm(displayTargetClass, reason.trim());
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save classification override.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return createPortal(
    <div ref={dialogRef} className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-slate-900/65  transition-opacity",
          isClosing ? "animate-modal-backdrop-exit" : "animate-modal-backdrop"
        )}
        onClick={() => { if (!isSubmitting) onClose(); }}
      />

      <div
        className={cn(
          "bg-card border border-slate-200/90 rounded-2xl shadow-2xl max-w-lg w-full max-h-[calc(100dvh-1.5rem)] sm:max-h-[90vh] flex flex-col overflow-hidden z-10 my-auto",
          isClosing ? "animate-modal-content-exit" : "animate-modal-content"
        )}
      >
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between bg-card flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-700 border border-amber-200 flex items-center justify-center font-semibold">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Correct classification
              </h2>
              <p className="text-[11px] text-slate-500">
                Correct AI Vision Classification • Egg #{displayScan.sequence_number || 'N/A'}
              </p>
            </div>
          </div>

          <CloseButton aria-label="Close classification correction" disabled={isSubmitting} onClick={() => { if (!isSubmitting) onClose(); }} />
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="p-4 sm:p-5 space-y-4 overflow-y-auto custom-scrollbar flex-1">
          {error && (
            <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs font-semibold text-red-700 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Class Shift Visualizer */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex items-center justify-between">
            <div className="text-center space-y-1">
              <span className="text-[10px] text-slate-400 font-bold uppercase block">AI Classified</span>
              <Badge type="fertility" value={currentClass} />
            </div>

            <div className="flex flex-col items-center">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Override</span>
              <div className="w-8 h-8 rounded-full bg-card border border-slate-200 flex items-center justify-center text-slate-400 ">
                <ArrowRight className="w-4 h-4 text-brand" />
              </div>
            </div>

            <div className="text-center space-y-1">
              <span className="text-[10px] text-brand font-bold uppercase block">Operator Corrected</span>
              <Badge type="fertility" value={displayTargetClass} />
            </div>
          </div>

          {/* Preset Justifications */}
          <div className="space-y-1.5">
            <p className="text-sm font-medium text-slate-700">Choose an inspection reason</p>
            <div className="space-y-1.5">
              {REASON_PRESETS[displayTargetClass]?.map((preset, idx) => (
                <button
                  type="button"
                  aria-pressed={reason === preset}
                  disabled={isSubmitting}
                  key={idx}
                  onClick={() => handleSelectPreset(preset)}
                  className={`w-full text-left p-2.5 rounded-lg border text-xs font-medium transition-all cursor-pointer flex items-start gap-2 ${
                    reason === preset
                      ? 'bg-maroon-50/60 border-[#800000] text-brand  font-semibold'
                      : 'bg-card border-slate-200 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <CheckCircle2 className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${reason === preset ? 'text-brand' : 'text-slate-300'}`} />
                  <span className="leading-snug">{preset}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Custom Audit Justification */}
          <div className="space-y-1.5">
            <label htmlFor="humanintheloopoverridemodal-field-1" className="text-xs font-bold text-slate-700 block">
              Inspection notes (required)
            </label>
            <textarea id="humanintheloopoverridemodal-field-1"
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Provide specific optical observation details..."
              disabled={isSubmitting}
              className="w-full p-3 text-base sm:text-sm bg-card border border-input rounded-lg text-foreground resize-y"
              required
            />
          </div>

          {/* Economic Notice */}
          {displayTargetClass === 'INFERTILE' && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 flex flex-wrap items-center justify-between gap-2">
              <span>Day 10 Commercial Penoy Salvage Recovery:</span>
              <strong className="text-amber-800 font-mono font-bold">+₱14.00/egg</strong>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => { if (!isSubmitting) onClose(); }}
              disabled={isSubmitting}
              className="secondary-action"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="primary-action"
            >
              {isSubmitting ? 'Saving correction…' : 'Save correction'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
};
