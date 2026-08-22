import React, { useState, useEffect } from 'react';
import {
  X,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react';
import { EggScan, FertilityClass } from '../types';
import { Badge } from './Badge';

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
  ABNORMAL: [
    'Blood ring / early dead embryo termination observed.',
    'Corrupted yolk / cloudiness culled to prevent incubator contamination.',
    'Cracked air cell / physical shell imperfection.',
  ],
};

export const HumanInTheLoopOverrideModal: React.FC<HumanInTheLoopOverrideModalProps> = ({
  isOpen,
  scan,
  targetClass,
  onClose,
  onConfirm,
}) => {
  const [reason, setReason] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (targetClass && REASON_PRESETS[targetClass]?.length > 0) {
      setReason(REASON_PRESETS[targetClass][0]);
    } else {
      setReason('Visual re-inspection by operator');
    }
    setError(null);
  }, [targetClass, isOpen]);

  if (!isOpen || !scan || !targetClass) return null;

  const currentClass = scan.final_class || 'FERTILE';

  const handleSelectPreset = (preset: string) => {
    setReason(preset);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError('Please provide or select a justification for the audit trail.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onConfirm(targetClass, reason.trim());
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save classification override.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-modal-backdrop">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden animate-modal-content">
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-700 flex items-center justify-center font-black">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Confirm Human-in-the-Loop Override
              </h2>
              <p className="text-[11px] text-slate-500">
                Scan #{(scan.sequence_number ?? 0).toString().padStart(3, '0')} • Batch: {scan.batch_id}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs font-semibold text-red-700 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Classification Transition Comparison */}
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between gap-3 text-xs">
            <div className="space-y-1">
              <span className="text-[10px] text-slate-500 font-semibold block uppercase">
                Original AI Output
              </span>
              <Badge type="fertility" value={currentClass} />
            </div>

            <div className="flex flex-col items-center justify-center text-slate-400">
              <ArrowRight className="w-4 h-4" />
              <span className="text-[9px] font-bold mt-0.5">RECLASSIFY</span>
            </div>

            <div className="space-y-1 text-right">
              <span className="text-[10px] text-slate-500 font-semibold block uppercase">
                Operator Target
              </span>
              <Badge type="fertility" value={targetClass} />
            </div>
          </div>

          {/* Preset Reason Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
              <span>Audit Justification Preset</span>
              <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
            </label>
            <div className="space-y-1.5">
              {REASON_PRESETS[targetClass]?.map((preset, index) => {
                const isSelected = reason === preset;
                return (
                  <button
                    key={index}
                    type="button"
                    onClick={() => handleSelectPreset(preset)}
                    className={`w-full text-left p-2 rounded-lg border text-xs transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-amber-50/70 border-amber-400 font-semibold text-amber-950 ring-1 ring-amber-400'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300'
                    }`}
                  >
                    {preset}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Custom Reason Textarea */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700">
              Custom Operator Remarks
            </label>
            <textarea
              rows={2}
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Provide a reason for the classification override..."
              className="w-full p-2.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-[#800000] focus:ring-1 focus:ring-[#800000]"
            />
          </div>

          {/* Audit Notice */}
          <div className="p-3 bg-amber-50/60 border border-amber-200 rounded-lg text-[11px] text-amber-900 flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <span>
              This action updates batch yield statistics and logs an immutable audit trail entry with your operator credentials and IP address.
            </span>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-3.5 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-semibold cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? 'Saving Override...' : 'Confirm & Log Override'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
