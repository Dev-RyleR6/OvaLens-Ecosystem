import React from 'react';
import { FertilityClass } from '../types';
import { Badge } from './Badge';

interface CandlingApertureProps {
  finalClass?: FertilityClass;
  confidence?: number;
  inferenceMs?: number;
  aspectRatio?: number;
  sequenceNumber?: number;
  batchId?: string;
}

export const CandlingAperture: React.FC<CandlingApertureProps> = ({
  finalClass = 'FERTILE',
  confidence = 0.948,
  inferenceMs = 26.4,
  aspectRatio = 0.78,
}) => {
  const isFertile = finalClass === 'FERTILE';
  const isInfertile = finalClass === 'INFERTILE';
  const isAbnormal = finalClass === 'ABNORMAL';

  return (
    <div className="space-y-3 group">
      {/* Visual Transillumination Canvas */}
      <div className="relative w-full h-52 bg-slate-950 rounded-xl border border-slate-800 overflow-hidden flex items-center justify-center transition-all duration-300 group-hover:border-slate-700">
        {/* Candling Strobe Light Source with subtle pulse */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(245,158,11,0.25)_0%,_rgba(0,0,0,0.85)_75%)] animate-pulse-glow" />

        {/* SVG Duck Egg Graphic */}
        <svg viewBox="0 0 400 500" className="w-32 h-44 z-10 filter drop-shadow-[0_0_14px_rgba(245,158,11,0.35)] transition-transform duration-300 group-hover:scale-105">
          <defs>
            <radialGradient id="eggGlowLight" cx="45%" cy="42%" r="60%">
              {isFertile && (
                <>
                  <stop offset="0%" stopColor="#FB923C" stopOpacity="0.95" />
                  <stop offset="45%" stopColor="#EA580C" stopOpacity="0.85" />
                  <stop offset="85%" stopColor="#7C2D12" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#290E05" stopOpacity="0.98" />
                </>
              )}
              {isInfertile && (
                <>
                  <stop offset="0%" stopColor="#FDE047" stopOpacity="0.95" />
                  <stop offset="50%" stopColor="#F59E0B" stopOpacity="0.85" />
                  <stop offset="90%" stopColor="#78350F" stopOpacity="0.95" />
                  <stop offset="100%" stopColor="#290E05" stopOpacity="0.98" />
                </>
              )}
              {isAbnormal && (
                <>
                  <stop offset="0%" stopColor="#F87171" stopOpacity="0.85" />
                  <stop offset="40%" stopColor="#B91C1C" stopOpacity="0.9" />
                  <stop offset="80%" stopColor="#450A0A" stopOpacity="0.95" />
                  <stop offset="100%" stopColor="#1A0303" stopOpacity="0.98" />
                </>
              )}
            </radialGradient>
          </defs>

          {/* Duck Egg Silhouette */}
          <path
            d="M 200,30 C 290,30 360,160 360,300 C 360,410 290,470 200,470 C 110,470 40,410 40,300 C 40,160 110,30 200,30 Z"
            fill="url(#eggGlowLight)"
            stroke="rgba(255,255,255,0.25)"
            strokeWidth="2"
          />

          {/* Air Cell */}
          <ellipse cx="200" cy="70" rx="90" ry="28" fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.2)" strokeDasharray="3 3" />

          {/* Biological Features */}
          {isFertile && (
            <g>
              <circle cx="180" cy="220" r="16" fill="#431407" />
              <path d="M 180,220 Q 140,180 100,160" fill="none" stroke="#7C2D12" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M 180,220 Q 220,170 270,150" fill="none" stroke="#7C2D12" strokeWidth="2" strokeLinecap="round" />
              <path d="M 180,220 Q 130,260 90,290" fill="none" stroke="#7C2D12" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M 180,220 Q 230,270 280,310" fill="none" stroke="#7C2D12" strokeWidth="2" strokeLinecap="round" />
            </g>
          )}

          {isInfertile && (
            <circle cx="200" cy="260" r="60" fill="rgba(217,119,6,0.35)" stroke="rgba(245,158,11,0.5)" strokeWidth="1.5" />
          )}

          {isAbnormal && (
            <g>
              <ellipse cx="195" cy="245" rx="55" ry="40" fill="none" stroke="#991B1B" strokeWidth="4" strokeDasharray="8 4" />
              <circle cx="195" cy="245" r="20" fill="#450A0A" />
            </g>
          )}
        </svg>

        {/* Optical Metadata Overlay */}
        <div className="absolute bottom-2.5 left-3 right-3 flex items-center justify-between text-[11px] text-white/90 bg-black/60 px-3 py-1 rounded-lg border border-white/10 backdrop-blur-xs">
          <span>YOLOv8 FP16 Transillumination</span>
          <span className="font-bold text-amber-400">{(confidence * 100).toFixed(1)}% Conf</span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
          <span className="text-[10px] text-slate-500 font-medium block">Class</span>
          <Badge type="fertility" value={finalClass} />
        </div>
        <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
          <span className="text-[10px] text-slate-500 font-medium block">Aspect Ratio</span>
          <span className="font-bold text-[#0F172A]">{aspectRatio.toFixed(2)}</span>
        </div>
        <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
          <span className="text-[10px] text-slate-500 font-medium block">Inference</span>
          <span className="font-bold text-[#0F172A]">{inferenceMs.toFixed(1)} ms</span>
        </div>
      </div>
    </div>
  );
};
