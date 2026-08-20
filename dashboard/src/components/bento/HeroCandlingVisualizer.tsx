import React, { useState } from 'react';
import { HelpCircle, Sparkles, Activity } from 'lucide-react';

interface HeroCandlingVisualizerProps {
  totalRevenue?: number;
  growthPct?: number;
  batchCode?: string;
  activeEmbryoCount?: number;
}

export const HeroCandlingVisualizer: React.FC<HeroCandlingVisualizerProps> = ({
  totalRevenue = 18540,
  growthPct = 12.4,
  batchCode = "BATCH-2026-08-KAY-01",
  activeEmbryoCount = 451,
}) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="bento-card p-5 flex flex-col justify-between h-full relative overflow-hidden">
      {/* Top Value Header */}
      <div>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-baseline gap-1">
              <span className="text-emerald-400 font-bold text-lg">₱</span>
              <span className="text-3xl font-extrabold tracking-tight text-white font-sans">
                {totalRevenue.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Yearly Hatchery Value: <strong className="text-slate-200">₱15,200.00 avg</strong>
            </p>
          </div>

          <div className="text-right">
            <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded-full inline-block">
              +{growthPct}% vs last cycle
            </span>
            <button
              onClick={() => setShowTooltip(!showTooltip)}
              className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center gap-1 mt-1 justify-end cursor-pointer"
            >
              <HelpCircle className="w-3 h-3" />
              <span>How it works?</span>
            </button>
          </div>
        </div>

        {showTooltip && (
          <div className="mt-2 p-2.5 bg-[#1A2234] border border-cyan-500/30 rounded-xl text-[11px] text-slate-300 leading-relaxed animate-in fade-in-50">
            Combined economic yield calculated from Day-10 Penoy food salvage (₱14/egg), incubator electricity savings (₱2.50/egg), and projected day-old duckling sales (₱40/duckling).
          </div>
        )}
      </div>

      {/* 3D-Style Transillumination Candling Visual Box (Hero Graphic) */}
      <div className="mt-4 relative rounded-2xl bg-gradient-to-b from-[#111A2E] via-[#0D1525] to-[#0A0E1A] border border-teal-500/30 p-4 h-48 overflow-hidden flex flex-col justify-between shadow-glow-cyan">
        {/* Optical Background Glow & Vignette */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(6,182,212,0.18)_0%,_rgba(16,185,129,0.12)_40%,_transparent_75%)] pointer-events-none" />

        {/* Floating Technical Badge */}
        <div className="relative z-10 flex items-center justify-between">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-teal-950/80 border border-teal-500/40 text-[11px] text-teal-300 font-medium">
            <Sparkles className="w-3 h-3 text-cyan-400 animate-pulse" />
            <span>AI Candling Engine</span>
          </div>

          <span className="text-[10px] font-mono text-slate-400 bg-black/40 px-2 py-0.5 rounded border border-white/5">
            {batchCode}
          </span>
        </div>

        {/* Stylized Candling Transillumination Chamber (SVG Canvas) */}
        <div className="relative z-10 my-auto flex items-center justify-center">
          <svg viewBox="0 0 320 180" className="w-full h-24 filter drop-shadow-[0_0_15px_rgba(6,182,212,0.4)]">
            <defs>
              {/* Candling Light Beam Gradient */}
              <linearGradient id="beamGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#06B6D4" stopOpacity="0.8" />
                <stop offset="50%" stopColor="#10B981" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#34D399" stopOpacity="0.7" />
              </linearGradient>

              {/* Egg Transillumination Radial */}
              <radialGradient id="heroEggGlow" cx="45%" cy="40%" r="60%">
                <stop offset="0%" stopColor="#34D399" stopOpacity="0.9" />
                <stop offset="45%" stopColor="#059669" stopOpacity="0.7" />
                <stop offset="85%" stopColor="#064E3B" stopOpacity="0.85" />
                <stop offset="100%" stopColor="#022C22" stopOpacity="0.95" />
              </radialGradient>
            </defs>

            {/* Geometric Transillumination Rays */}
            <polygon points="40,20 160,70 40,160" fill="url(#beamGrad)" opacity="0.25" />
            <polygon points="280,20 160,70 280,160" fill="url(#beamGrad)" opacity="0.25" />

            {/* Duck Egg Contour at Center */}
            <g transform="translate(130, 20)">
              <path
                d="M 30,5 C 50,5 65,30 65,60 C 65,85 50,95 30,95 C 10,95 -5,85 -5,60 C -5,30 10,5 30,5 Z"
                fill="url(#heroEggGlow)"
                stroke="#34D399"
                strokeWidth="1.5"
                strokeOpacity="0.8"
              />
              {/* Spider Blood Vessels */}
              <circle cx="28" cy="45" r="5" fill="#064E3B" />
              <path d="M 28,45 Q 18,30 8,25" fill="none" stroke="#047857" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M 28,45 Q 38,30 50,28" fill="none" stroke="#047857" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M 28,45 Q 18,60 8,70" fill="none" stroke="#047857" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M 28,45 Q 38,62 52,68" fill="none" stroke="#047857" strokeWidth="1.5" strokeLinecap="round" />
            </g>

            {/* Waveform Line beneath egg */}
            <path
              d="M 10,140 Q 60,110 110,140 T 210,140 T 310,140"
              fill="none"
              stroke="#06B6D4"
              strokeWidth="2"
              strokeDasharray="4 3"
              opacity="0.6"
            />
          </svg>
        </div>

        {/* Active Telemetry Prompt Footer */}
        <div className="relative z-10 flex items-center justify-between text-[11px] text-slate-300">
          <span className="font-medium text-cyan-300 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            YOLOv8 FP16 verifying Day-10 Spider Veins...
          </span>
          <span className="font-bold text-white font-mono">{activeEmbryoCount} Viable</span>
        </div>
      </div>
    </div>
  );
};
