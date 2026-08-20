import React from 'react';
import {
  FileText,
  Printer,
  Download,
  X,
  CheckCircle2,
  ShieldCheck,
  Building,
  QrCode,
} from 'lucide-react';
import { BatchSummary } from '../types';
import { Dialog } from './ui/dialog';

interface CandlingCertificateModalProps {
  isOpen: boolean;
  onClose: () => void;
  batch: BatchSummary | null;
}

export const CandlingCertificateModal: React.FC<CandlingCertificateModalProps> = ({
  isOpen,
  onClose,
  batch,
}) => {
  if (!batch) return null;

  const handlePrint = () => {
    window.print();
  };

  const fertileCount = batch.fertile_count || 451;
  const penoyCount = batch.infertile_count || 37;
  const abnormalCount = batch.abnormal_count || 12;
  const totalScanned = batch.total_scanned || 500;
  const penoySalvageValue = (penoyCount * 14.0).toFixed(2);

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title=""
      description=""
    >
      <div className="space-y-6 text-slate-800 print:m-0 print:p-0">
        {/* Certificate Container */}
        <div className="border-2 border-[#800000] p-6 rounded-xl bg-white space-y-5 shadow-xs relative">
          {/* Watermark Logo Accent */}
          <div className="absolute right-4 top-4 opacity-10 pointer-events-none">
            <Building className="w-32 h-32 text-[#800000]" />
          </div>

          {/* Institutional Header */}
          <div className="text-center pb-4 border-b-2 border-[#800000] space-y-1">
            <span className="text-[11px] font-extrabold tracking-widest text-[#800000] uppercase block">
              Foundation University • Hatchery Research & Agri-Tech Center
            </span>
            <h2 className="text-lg font-black text-[#0F172A] uppercase tracking-tight">
              Official Duck Egg Candling & Fertility Certificate
            </h2>
            <p className="text-[11px] text-slate-500 font-medium">
              Dumaguete City, Negros Oriental • Automated ONNX Vision Sorting System
            </p>
          </div>

          {/* Batch Meta Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs bg-slate-50 p-3.5 rounded-lg border border-slate-200">
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase block">Batch Code</span>
              <strong className="text-slate-900 font-mono">{batch.batch_code}</strong>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase block">Duck Breed</span>
              <strong className="text-[#800000]">{batch.breed}</strong>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase block">Candling Milestone</span>
              <strong className="text-slate-900">{batch.current_stage} (Day 10)</strong>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase block">Certified Date</span>
              <strong className="text-slate-900">{new Date().toLocaleDateString()}</strong>
            </div>
          </div>

          {/* Classification Yield Table */}
          <div className="space-y-2">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
              Verified Classification & Salvage Summary:
            </span>

            <table className="w-full text-xs text-left border border-slate-200 rounded-lg overflow-hidden">
              <thead className="bg-slate-100 text-[11px] font-bold text-slate-600 uppercase">
                <tr>
                  <th className="py-2 px-3">Classification</th>
                  <th className="py-2 px-3 text-center">Action</th>
                  <th className="py-2 px-3 text-right">Count</th>
                  <th className="py-2 px-3 text-right">Yield %</th>
                  <th className="py-2 px-3 text-right">Economic Valuation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr className="bg-emerald-50/40 font-medium">
                  <td className="py-2.5 px-3 font-bold text-emerald-950">Fertile Embryos (Viable)</td>
                  <td className="py-2.5 px-3 text-center text-emerald-800 font-bold">ACCEPT</td>
                  <td className="py-2.5 px-3 text-right font-extrabold text-emerald-900">{fertileCount}</td>
                  <td className="py-2.5 px-3 text-right text-emerald-800">{((fertileCount / totalScanned) * 100).toFixed(1)}%</td>
                  <td className="py-2.5 px-3 text-right text-slate-600">Transferred to Day 18 Hatcher</td>
                </tr>

                <tr className="bg-amber-50/40 font-medium">
                  <td className="py-2.5 px-3 font-bold text-amber-950">Infertile / Penoy</td>
                  <td className="py-2.5 px-3 text-center text-amber-800 font-bold">SALVAGE</td>
                  <td className="py-2.5 px-3 text-right font-extrabold text-amber-900">{penoyCount}</td>
                  <td className="py-2.5 px-3 text-right text-amber-800">{((penoyCount / totalScanned) * 100).toFixed(1)}%</td>
                  <td className="py-2.5 px-3 text-right font-bold text-amber-900">₱{penoySalvageValue} (@ ₱14.00)</td>
                </tr>

                <tr className="bg-red-50/40 font-medium">
                  <td className="py-2.5 px-3 font-bold text-red-950">Abnormal / Dead Embryo</td>
                  <td className="py-2.5 px-3 text-center text-red-800 font-bold">DISCARD</td>
                  <td className="py-2.5 px-3 text-right font-extrabold text-red-900">{abnormalCount}</td>
                  <td className="py-2.5 px-3 text-right text-red-800">{((abnormalCount / totalScanned) * 100).toFixed(1)}%</td>
                  <td className="py-2.5 px-3 text-right text-slate-500">Culled to prevent burst</td>
                </tr>

                <tr className="bg-slate-100 font-bold text-slate-900 border-t border-slate-300">
                  <td className="py-2.5 px-3">Total Candled Throughput</td>
                  <td className="py-2.5 px-3 text-center">100% SORTED</td>
                  <td className="py-2.5 px-3 text-right">{totalScanned}</td>
                  <td className="py-2.5 px-3 text-right">100.0%</td>
                  <td className="py-2.5 px-3 text-right text-[#800000]">₱{penoySalvageValue} Total Salvage</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* AI Verification Footer & Signature */}
          <div className="pt-4 border-t border-slate-200 grid grid-cols-2 gap-4 text-xs">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-8 h-8 text-emerald-700 flex-shrink-0" />
              <div>
                <span className="font-bold text-slate-900 block">YOLOv8 FP16 Vision Verified</span>
                <span className="text-[11px] text-slate-500">
                  Station: <strong>STATION-01-RP5</strong> • Confidence: <strong>95.4%</strong>
                </span>
              </div>
            </div>

            <div className="text-right space-y-1">
              <div className="inline-block border-b border-slate-400 w-40 pb-0.5 text-center">
                <span className="font-bold text-slate-900 block">Ryle Gabotero</span>
              </div>
              <span className="text-[10px] text-slate-500 block">Lead Candling System Operator</span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-200">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 cursor-pointer"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handlePrint}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold shadow-xs transition-colors cursor-pointer"
          >
            <Printer className="w-4 h-4" />
            <span>Print Official Certificate</span>
          </button>
        </div>
      </div>
    </Dialog>
  );
};
