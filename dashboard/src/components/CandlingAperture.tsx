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
  className?: string;
}

export const CandlingAperture: React.FC<CandlingApertureProps> = ({
  finalClass = 'FERTILE',
  confidence = 0.948,
  inferenceMs = 26.4,
  aspectRatio = 0.78,
  sequenceNumber = 42,
  batchId = 'BATCH-2026-08-KAY-01',
  className = '',
}) => {
  const isFertile = finalClass === 'FERTILE';
  const isInfertile = finalClass === 'INFERTILE';
  const isAbnormal = finalClass === 'ABNORMAL';

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Visual Canvas Container */}
      <div className="relative w-full h-56 bg-neutral-950 rounded-lg border overflow-hidden flex items-center justify-center">
        {/* Soft Candling Transillumination Light Background */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(245,158,11,0.25)_0%,_rgba(0,0,0,0.85)_75%)]" />

        {/* SVG Transillumination */}
        <svg viewBox="0 0 400 500" className="w-36 h-48 z-10">
          <defs>
            <radialGradient id="eggTransillumination" cx="45%" cy="42%" r="60%">
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

          {/* Duck Egg Contour */}
          <path
            d="M 200,30 C 290,30 360,160 360,300 C 360,410 290,470 200,470 C 110,470 40,410 40,300 C 40,160 110,30 200,30 Z"
            fill="url(#eggTransillumination)"
            stroke="rgba(255,255,255,0.2)"
            strokeWidth="2"
          />

          {/* Air Cell */}
          <ellipse cx="200" cy="70" rx="90" ry="28" fill="rgba(255,255,255,0.15)" stroke="rgba(255,255,255,0.25)" strokeDasharray="3 3" />

          {/* Biological Features */}
          {isFertile && (
            <g>
              <circle cx="180" cy="220" r="18" fill="#431407" />
              <path d="M 180,220 Q 140,180 100,160" fill="none" stroke="#7C2D12" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M 180,220 Q 220,170 270,150" fill="none" stroke="#7C2D12" strokeWidth="2" strokeLinecap="round" />
              <path d="M 180,220 Q 130,260 90,290" fill="none" stroke="#7C2D12" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M 180,220 Q 230,270 280,310" fill="none" stroke="#7C2D12" strokeWidth="2" strokeLinecap="round" />
            </g>
          )}

          {isInfertile && (
            <g>
              <circle cx="200" cy="260" r="65" fill="rgba(217,119,6,0.3)" stroke="rgba(245,158,11,0.4)" strokeWidth="1.5" />
            </g>
          )}

          {isAbnormal && (
            <g>
              <ellipse cx="195" cy="245" rx="60" ry="45" fill="none" stroke="#991B1B" strokeWidth="5" strokeDasharray="10 4" />
              <circle cx="195" cy="245" r="22" fill="#450A0A" />
            </g>
          )}
        </svg>

        {/* Clean Detection Label */}
        <div className="absolute bottom-2.5 left-3 right-3 flex items-center justify-between text-[11px] text-white/90 bg-black/60 backdrop-blur-xs px-2.5 py-1 rounded border border-white/10">
          <span>YOLOv8 Detection</span>
          <span>{(confidence * 100).toFixed(1)}% ({inferenceMs.toFixed(0)}ms)</span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="p-2 bg-muted/40 rounded border">
          <span className="text-[10px] text-muted-foreground block">Class</span>
          <Badge type="fertility" value={finalClass} />
        </div>
        <div className="p-2 bg-muted/40 rounded border">
          <span className="text-[10px] text-muted-foreground block">Aspect Ratio</span>
          <span className="font-semibold text-foreground">{aspectRatio.toFixed(2)}</span>
        </div>
        <div className="p-2 bg-muted/40 rounded border">
          <span className="text-[10px] text-muted-foreground block">Inference</span>
          <span className="font-semibold text-foreground">{inferenceMs.toFixed(1)} ms</span>
        </div>
      </div>
    </div>
  );
};
