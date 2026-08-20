import React, { useState } from 'react';
import { Eye, Layers, Activity, Sliders, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';
import { FertilityClass } from '../types';

interface CandlingApertureProps {
  finalClass?: FertilityClass;
  confidence?: number;
  inferenceMs?: number;
  aspectRatio?: number;
  meanLuminance?: number;
  sequenceNumber?: number;
  batchId?: string;
}

export const CandlingAperture: React.FC<CandlingApertureProps> = ({
  finalClass = 'FERTILE',
  confidence = 0.948,
  inferenceMs = 26.4,
  aspectRatio = 0.78,
  meanLuminance = 184.2,
  sequenceNumber = 42,
  batchId = 'BATCH-2026-08-KAY-01',
}) => {
  // Layer toggles
  const [showHud, setShowHud] = useState(true);
  const [showVeins, setShowVeins] = useState(true);
  const [showWaveform, setShowWaveform] = useState(false);
  const [opticalFilter, setOpticalFilter] = useState<'STANDARD' | 'CONTRAST' | 'HEATMAP'>('STANDARD');

  const isFertile = finalClass === 'FERTILE';
  const isInfertile = finalClass === 'INFERTILE';
  const isAbnormal = finalClass === 'ABNORMAL';

  return (
    <div className="panel-scada p-4 space-y-4">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-obsidian-700/60 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-[#800000]/20 rounded border border-[#800000]/50 text-amber-400">
            <Eye className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-display font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
              Optical Candling Aperture & Spectral Layer Inspector
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-obsidian-800 border border-obsidian-600 rounded text-emerald-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-led-pulse" />
                ACTIVE YOLOv8 FP16
              </span>
            </h3>
            <p className="text-[10px] font-mono text-slate-400">
              Seq: <strong className="text-amber-300">#{sequenceNumber.toString().padStart(3, '0')}</strong> • Batch: <strong className="text-slate-200">{batchId}</strong>
            </p>
          </div>
        </div>

        {/* Optical Layer Filter Toggles */}
        <div className="flex items-center gap-1.5 text-xs font-mono">
          <button
            onClick={() => setShowHud(!showHud)}
            className={`px-2 py-1 rounded border text-[10px] font-bold transition-colors ${
              showHud ? 'bg-[#800000] border-[#991B1B] text-white' : 'bg-obsidian-800 border-obsidian-700 text-slate-400'
            }`}
          >
            YOLO HUD: {showHud ? 'ON' : 'OFF'}
          </button>
          <button
            onClick={() => setShowVeins(!showVeins)}
            className={`px-2 py-1 rounded border text-[10px] font-bold transition-colors ${
              showVeins ? 'bg-emerald-900 border-emerald-700 text-emerald-200' : 'bg-obsidian-800 border-obsidian-700 text-slate-400'
            }`}
          >
            VEIN MASK: {showVeins ? 'ON' : 'OFF'}
          </button>
          <button
            onClick={() => setShowWaveform(!showWaveform)}
            className={`px-2 py-1 rounded border text-[10px] font-bold transition-colors ${
              showWaveform ? 'bg-amber-900 border-amber-700 text-amber-200' : 'bg-obsidian-800 border-obsidian-700 text-slate-400'
            }`}
          >
            HISTOGRAM: {showWaveform ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      {/* Main Optical Candling Viewport (High-Contrast Transillumination Canvas) */}
      <div className="relative w-full h-64 sm:h-72 bg-black rounded border border-obsidian-700 overflow-hidden flex items-center justify-center">
        {/* Physical Candling Light Tunnel Vignette & Optical Aperture */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(245,158,11,0.35)_0%,_rgba(180,83,9,0.15)_40%,_rgba(5,5,10,0.95)_75%,_#000000_100%)]" />

        {/* Reticle / Optical Crosshairs Grid */}
        <div className="absolute inset-0 opacity-15 bg-[linear-gradient(to_right,#ffffff_1px,transparent_1px),linear-gradient(to_bottom,#ffffff_1px,transparent_1px)] bg-[size:32px_32px]" />

        {/* Central Candling Aperture Ring (10W Cree Lamp Tunnel) */}
        <div className="absolute w-52 h-64 rounded-[50%_50%_46%_46%] border border-amber-500/20 shadow-[0_0_50px_rgba(245,158,11,0.2)]" />

        {/* SVG High-Fidelity Egg Transillumination & Biological Structures */}
        <svg
          viewBox="0 0 400 500"
          className="w-48 h-60 z-10 filter drop-shadow-[0_0_25px_rgba(245,158,11,0.4)]"
        >
          <defs>
            {/* Candling Light Glow Gradient */}
            <radialGradient id="eggGlow" cx="45%" cy="40%" r="60%">
              {isFertile && (
                <>
                  <stop offset="0%" stopColor="#FB923C" stopOpacity="0.95" />
                  <stop offset="40%" stopColor="#EA580C" stopOpacity="0.85" />
                  <stop offset="75%" stopColor="#9A3412" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#431407" stopOpacity="0.98" />
                </>
              )}
              {isInfertile && (
                <>
                  <stop offset="0%" stopColor="#FDE047" stopOpacity="0.98" />
                  <stop offset="50%" stopColor="#F59E0B" stopOpacity="0.9" />
                  <stop offset="85%" stopColor="#B45309" stopOpacity="0.95" />
                  <stop offset="100%" stopColor="#78350F" stopOpacity="0.98" />
                </>
              )}
              {isAbnormal && (
                <>
                  <stop offset="0%" stopColor="#F87171" stopOpacity="0.8" />
                  <stop offset="35%" stopColor="#B91C1C" stopOpacity="0.9" />
                  <stop offset="70%" stopColor="#7F1D1D" stopOpacity="0.95" />
                  <stop offset="100%" stopColor="#450A0A" stopOpacity="0.98" />
                </>
              )}
            </radialGradient>
          </defs>

          {/* Duck Egg Silhouette Path */}
          <path
            d="M 200,30 C 290,30 360,160 360,300 C 360,410 290,470 200,470 C 110,470 40,410 40,300 C 40,160 110,30 200,30 Z"
            fill="url(#eggGlow)"
            stroke={isFertile ? '#F97316' : isInfertile ? '#FBBF24' : '#EF4444'}
            strokeWidth="2"
            strokeOpacity="0.6"
          />

          {/* Air Cell Aperture on Blunt End */}
          <ellipse cx="200" cy="70" rx="90" ry="30" fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.2)" strokeDasharray="3 3" />

          {/* Biological Embryonic Structures */}
          {isFertile && showVeins && (
            <g className="transition-opacity duration-300">
              {/* Embryo Eye & Core */}
              <circle cx="180" cy="220" r="22" fill="#7C2D12" stroke="#431407" strokeWidth="2" />
              <circle cx="178" cy="216" r="6" fill="#1C1917" />

              {/* Spider Blood Vessels (Radial Arterioles) */}
              <path d="M 180,220 Q 140,180 100,160 Q 80,150 60,170" fill="none" stroke="#7C2D12" strokeWidth="3" strokeLinecap="round" />
              <path d="M 180,220 Q 220,170 270,150 Q 310,140 330,165" fill="none" stroke="#7C2D12" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M 180,220 Q 130,260 90,290 Q 70,310 65,350" fill="none" stroke="#7C2D12" strokeWidth="3" strokeLinecap="round" />
              <path d="M 180,220 Q 230,270 280,310 Q 320,340 340,380" fill="none" stroke="#7C2D12" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M 180,220 Q 185,320 190,390 Q 192,420 185,450" fill="none" stroke="#7C2D12" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M 140,180 Q 130,140 120,110" fill="none" stroke="#9A3412" strokeWidth="1.5" />
              <path d="M 220,170 Q 240,130 250,100" fill="none" stroke="#9A3412" strokeWidth="1.5" />
              <path d="M 130,260 Q 100,265 75,250" fill="none" stroke="#9A3412" strokeWidth="1.5" />
              <path d="M 230,270 Q 265,275 300,260" fill="none" stroke="#9A3412" strokeWidth="1.5" />
            </g>
          )}

          {isInfertile && (
            <g>
              {/* Clean clear unfertilized yolk shadow */}
              <circle cx="200" cy="260" r="70" fill="rgba(217,119,6,0.35)" stroke="rgba(245,158,11,0.5)" strokeWidth="1.5" />
              <circle cx="200" cy="260" r="45" fill="rgba(245,158,11,0.25)" />
            </g>
          )}

          {isAbnormal && (
            <g>
              {/* Blood ring / corrupted dead yolk */}
              <ellipse cx="195" cy="245" rx="65" ry="50" fill="none" stroke="#991B1B" strokeWidth="6" strokeDasharray="12 4" />
              <circle cx="195" cy="245" r="28" fill="#450A0A" />
            </g>
          )}
        </svg>

        {/* YOLOv8 Bounding Box HUD Overlay */}
        {showHud && (
          <div className="absolute inset-8 sm:inset-10 border-2 border-dashed border-amber-400/80 rounded pointer-events-none flex flex-col justify-between p-2 z-20">
            <div className="flex items-center justify-between">
              <div className="bg-obsidian-950/90 border border-amber-500/70 text-amber-300 px-2 py-0.5 rounded text-[10px] font-mono font-bold flex items-center gap-1.5 shadow-lg">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                {finalClass} • {(confidence * 100).toFixed(1)}%
              </div>
              <div className="bg-obsidian-950/90 border border-obsidian-700 text-slate-300 px-2 py-0.5 rounded text-[10px] font-mono">
                {inferenceMs.toFixed(1)} ms
              </div>
            </div>

            <div className="flex items-center justify-between text-[9px] font-mono text-slate-400 bg-obsidian-950/80 px-2 py-0.5 rounded self-end">
              <span>AR: {aspectRatio.toFixed(2)} (VALID)</span>
            </div>
          </div>
        )}

        {/* Live Histogram Waveform Overlay */}
        {showWaveform && (
          <div className="absolute bottom-2 left-2 right-2 bg-obsidian-950/90 border border-obsidian-700 rounded p-2 z-30 flex items-center justify-between">
            <span className="text-[9px] font-mono text-amber-300 font-bold">HSV OPTICAL LUMINANCE SPECTRUM</span>
            <div className="flex items-end gap-1 h-6 w-48">
              {[12, 18, 35, 62, 85, 98, 92, 74, 55, 38, 22, 14].map((val, idx) => (
                <div
                  key={idx}
                  className="flex-1 bg-amber-400/80 rounded-t"
                  style={{ height: `${val}%` }}
                />
              ))}
            </div>
            <span className="text-[9px] font-mono text-slate-400">μ={meanLuminance}</span>
          </div>
        )}
      </div>

      {/* Optical Telemetry Status Line */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
        <div className="p-2 bg-obsidian-950 rounded border border-obsidian-800">
          <span className="text-[10px] text-slate-500 block">CLASSIFICATION</span>
          <span className={`font-bold ${isFertile ? 'text-emerald-400' : isInfertile ? 'text-amber-300' : 'text-rose-400'}`}>
            {finalClass}
          </span>
        </div>
        <div className="p-2 bg-obsidian-950 rounded border border-obsidian-800">
          <span className="text-[10px] text-slate-500 block">ASPECT RATIO (AR)</span>
          <span className="font-bold text-slate-200">{aspectRatio.toFixed(2)} (0.65–1.45)</span>
        </div>
        <div className="p-2 bg-obsidian-950 rounded border border-obsidian-800">
          <span className="text-[10px] text-slate-500 block">MEAN LUMINANCE (HSV)</span>
          <span className="font-bold text-slate-200">{meanLuminance} / 255</span>
        </div>
        <div className="p-2 bg-obsidian-950 rounded border border-obsidian-800">
          <span className="text-[10px] text-slate-500 block">INFERENCE LATENCY</span>
          <span className="font-bold text-emerald-400">{inferenceMs.toFixed(1)} ms</span>
        </div>
      </div>
    </div>
  );
};
